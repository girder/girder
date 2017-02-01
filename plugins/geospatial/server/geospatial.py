#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import six

from geojson import GeoJSON
from pymongo import GEOSPHERE
from pymongo.errors import OperationFailure

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, RestException
from girder.constants import AccessType


GEOSPATIAL_FIELD = 'geo'


class GeospatialItem(Resource):
    """
    Geospatial methods added to the API endpoint for items.
    """

    @access.user
    @autoDescribeRoute(
        Description('Create new items from a GeoJSON feature or feature collection.')
        .modelParam('folderId', 'The ID of the parent folder.', model='folder',
                    level=AccessType.WRITE, paramType='formData')
        .jsonParam('geoJSON', 'A GeoJSON object containing the features or feature'
                   ' collection to add.')
        .errorResponse()
        .errorResponse('Invalid GeoJSON was passed in request body.')
        .errorResponse('GeoJSON feature or feature collection was not passed in'
                       ' request body.')
        .errorResponse("GeoJSON feature did not contain a property named"
                       " 'name'.")
        .errorResponse('Property name was invalid.')
        .errorResponse('Write access was denied on the parent folder.', 403)
        .notes("All GeoJSON features must contain a property named 'name' from"
               " which the name of each created item is taken.")
    )
    def create(self, folder, geoJSON, params):
        try:
            GeoJSON.to_instance(geoJSON, strict=True)
        except ValueError:
            raise RestException('Invalid GeoJSON passed in request body.')

        if geoJSON['type'] == 'Feature':
            features = [geoJSON]
        elif geoJSON['type'] == 'FeatureCollection':
            features = geoJSON['features']
        else:
            raise RestException('GeoJSON feature or feature collection must be '
                                'passed in request body.')

        data = []

        for feature in features:
            properties = feature['properties']
            if 'name' not in properties:
                raise RestException("All GeoJSON features must contain a"
                                    " property named 'name'.")
            name = properties['name']
            del properties['name']
            if 'description' in properties:
                description = properties['description']
                del properties['description']
            else:
                description = ''

            for key in properties:
                if not len(key):
                    raise RestException('Property names must be at least one'
                                        ' character long.')
                if '.' in key or key[0] == '$':
                    raise RestException('The property name %s must not contain'
                                        ' a period or begin with a dollar sign.' % key)

            data.append({'name': name,
                         'description': description,
                         'metadata': properties,
                         'geometry': feature['geometry']})

        user = self.getCurrentUser()

        items = []

        for datum in data:
            newItem = self.model('item').createItem(
                folder=folder, name=datum['name'], creator=user,
                description=datum['description'])
            self.model('item').setMetadata(newItem, datum['metadata'])
            newItem[GEOSPATIAL_FIELD] = {'geometry': datum['geometry']}
            newItem = self.model('item').updateItem(newItem)
            items.append(newItem)

        return [self._filter(item) for item in items]

    @access.public
    @autoDescribeRoute(
        Description('Search for an item by geospatial data.')
        .jsonParam('q', 'Search query as a JSON object.')
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
    )
    def find(self, q, limit, offset, sort, params):
        return self._find(q, limit, offset, sort)

    @access.public
    @autoDescribeRoute(
        Description('Search for items that intersects with a GeoJSON object.')
        .param('field', 'Name of field containing GeoJSON on which to search.', strip=True)
        .jsonParam('geometry', 'Search query condition as a GeoJSON object.')
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
    )
    def intersects(self, field, geometry, limit, offset, sort, params):
        try:
            GeoJSON.to_instance(geometry, strict=True)
        except (TypeError, ValueError):
            raise RestException("Invalid GeoJSON passed as 'geometry' parameter.")

        if field[:3] != '%s.' % GEOSPATIAL_FIELD:
            field = '%s.%s' % (GEOSPATIAL_FIELD, field)

        query = {
            field: {
                '$geoIntersects': {
                    '$geometry': geometry
                }
            }
        }

        return self._find(query, limit, offset, sort)

    def _getGeometry(self, geometry):
        try:
            GeoJSON.to_instance(geometry, strict=True)

            if geometry['type'] != 'Point':
                raise ValueError

            return geometry
        except (TypeError, ValueError):
            raise RestException("Invalid GeoJSON passed as 'geometry' parameter.")

    @access.public
    @autoDescribeRoute(
        Description('Search for items that are in proximity to a GeoJSON point.')
        .param('field', 'Name of field containing GeoJSON on which to search.', strip=True)
        .jsonParam('geometry', 'Search query condition as a GeoJSON point.')
        .param('maxDistance', 'Limits results to items that are at most this distance '
               'in meters from the GeoJSON point.', required=False, dataType='number')
        .param('minDistance', 'Limits results to items that are at least this distance '
               'in meters from the GeoJSON point.', required=False, dataType='number')
        .param('ensureIndex', 'Create a 2dsphere index on the field on which to search '
               'if one does not exist.', required=False, dataType='boolean', default=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Field on which to search was not indexed.')
        .errorResponse('Index creation was denied.', 403)
        .notes("Field on which to search be indexed by a 2dsphere index."
               " Anonymous users may not use 'ensureIndex' to create such an index.")
    )
    def near(self, field, geometry, maxDistance, minDistance, ensureIndex, limit,
             offset, sort, params):
        condition = {
            '$geometry': self._getGeometry(geometry)
        }

        if maxDistance is not None:
            if maxDistance < 0:
                raise RestException('maxDistance must be positive.')
            condition['$maxDistance'] = maxDistance
        if minDistance is not None:
            if minDistance < 0:
                raise RestException('minDistance must be positive.')
            condition['$minDistance'] = minDistance

        if field[:3] != '%s.' % GEOSPATIAL_FIELD:
            field = '%s.%s' % (GEOSPATIAL_FIELD, field)

        if ensureIndex:
            user = self.getCurrentUser()

            if not user:
                raise RestException('Index creation denied.', 403)

            self.model('item').collection.create_index([(field, GEOSPHERE)])

        query = {
            field: {
                '$near': condition
            }
        }

        try:
            return self._find(query, limit, offset, sort)
        except OperationFailure:
            raise RestException("Field '%s' must be indexed by a 2dsphere index." % field)

    _RADIUS_OF_EARTH = 6378137.0  # average in meters

    @access.public
    @autoDescribeRoute(
        Description('Search for items that are entirely within either a GeoJSON'
                    ' polygon or a circular region.')
        .param('field', 'Name of field containing GeoJSON on which to search.', strip=True)
        .jsonParam('geometry', 'Search query condition as a GeoJSON polygon.',
                   required=False)
        .jsonParam('center', 'Center of search radius as a GeoJSON point.',
                   required=False, requireObject=True)
        .param('radius', 'Search radius in meters.', required=False,
               dataType='number')
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Field on which to search was not indexed.')
        .errorResponse('Index creation was denied.', 403)
        .notes("Either parameter 'geometry' or both parameters 'center' "
               " and 'radius' are required.")
    )
    def within(self, field, geometry, center, radius, limit, offset, sort, params):
        if geometry is not None:
            try:
                GeoJSON.to_instance(geometry, strict=True)

                if geometry['type'] != 'Polygon':
                    raise ValueError
            except (TypeError, ValueError):
                raise RestException("Invalid GeoJSON passed as 'geometry' parameter.")

            condition = {
                '$geometry': geometry
            }

        elif center is not None and radius is not None:
            try:
                radius /= self._RADIUS_OF_EARTH

                if radius < 0.0:
                    raise ValueError
            except ValueError:
                raise RestException("Parameter 'radius' must be a number.")

            try:
                GeoJSON.to_instance(center, strict=True)

                if center['type'] != 'Point':
                    raise ValueError
            except (TypeError, ValueError):
                raise RestException("Invalid GeoJSON passed as 'center' parameter.")

            condition = {
                '$centerSphere': [center['coordinates'], radius]
            }

        else:
            raise RestException("Either parameter 'geometry' or both parameters"
                                " 'center' and 'radius' are required.")

        if field[:3] != '%s.' % GEOSPATIAL_FIELD:
            field = '%s.%s' % (GEOSPATIAL_FIELD, field)

        query = {
            field: {
                '$geoWithin': condition
            }
        }

        return self._find(query, limit, offset, sort)

    @access.public
    @autoDescribeRoute(
        Description('Get an item and its geospatial data by ID.')
        .modelParam('id', 'The ID of the item.', model='item', level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getGeospatial(self, item, params):
        return self._filter(item)

    @access.user
    @autoDescribeRoute(
        Description('Set geospatial fields on an item.')
        .notes('Set geospatial fields to null to delete them.')
        .modelParam('id', 'The ID of the item.', model='item', level=AccessType.WRITE)
        .jsonParam('geospatial', 'A JSON object containing the geospatial fields to add.',
                   paramType='body')
        .errorResponse('ID was invalid.')
        .errorResponse('Invalid JSON was passed in request body.')
        .errorResponse('Geospatial key name was invalid.')
        .errorResponse('Geospatial field did not contain valid GeoJSON.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    def setGeospatial(self, item, geospatial, params):
        for k, v in six.viewitems(geospatial):
            if '.' in k or k[0] == '$':
                raise RestException('Geospatial key name %s must not contain a'
                                    ' period or begin with a dollar sign.' % k)
            if v:
                try:
                    GeoJSON.to_instance(v, strict=True)
                except ValueError:
                    raise RestException('Geospatial field with key %s does not'
                                        ' contain valid GeoJSON: %s' % (k, v))

        if GEOSPATIAL_FIELD not in item:
            item[GEOSPATIAL_FIELD] = dict()

        item[GEOSPATIAL_FIELD].update(six.viewitems(geospatial))
        keys = [k for k, v in six.viewitems(item[GEOSPATIAL_FIELD]) if v is None]

        for key in keys:
            del item[GEOSPATIAL_FIELD][key]

        item = self.model('item').updateItem(item)

        return self._filter(item)

    def _filter(self, item):
        """
        Helper to filter the fields of an item and append its geospatial data.

        :param item: item whose fields to filter and geospatial data append.
        :type item: dict[str, unknown]
        :returns: filtered fields of the item with geospatial data appended to
                 its 'geo' field.
        :rtype : dict[str, unknown]
        """
        filtered = self.model('item').filter(item)

        if GEOSPATIAL_FIELD in item:
            filtered[GEOSPATIAL_FIELD] = item[GEOSPATIAL_FIELD]
        else:
            filtered[GEOSPATIAL_FIELD] = {}

        return filtered

    def _find(self, query, limit, offset, sort):
        """
        Helper to search the geospatial data of items and return the filtered
        fields and geospatial data of the matching items.

        :param query: geospatial search query.
        :type query: dict[str, unknown]
        :param limit: maximum number of matching items to return.
        :type limit: int
        :param offset: offset of matching items to return.
        :type offset: int
        :param sort: field by which to sort the matching items
        :type sort: str
        :returns: filtered fields of the matching items with geospatial data
                 appended to the 'geo' field of each item.
        :rtype : list[dict[str, unknown]]
        """
        user = self.getCurrentUser()
        cursor = self.model('item').find(query, sort=sort)

        return [self._filter(result) for result in
                self.model('item')
                    .filterResultsByPermission(cursor, user, AccessType.READ,
                                               limit, offset)]
