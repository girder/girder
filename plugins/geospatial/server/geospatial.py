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


import bson.json_util
import six

from geojson import GeoJSON
from pymongo import GEOSPHERE
from pymongo.errors import OperationFailure

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import loadmodel, Resource, RestException
from girder.constants import AccessType


GEOSPATIAL_FIELD = 'geo'


class GeospatialItem(Resource):
    """
    Geospatial methods added to the API endpoint for items.
    """

    @access.user
    @describeRoute(
        Description('Create new items from a GeoJSON feature or feature'
                    ' collection.')
        .param('folderId', 'The ID of the parent folder.', required=True,
               paramType='query')
        .param('geoJSON', 'A GeoJSON object containing the features or feature'
                          ' collection to add.', required=True,
               paramType='query')
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
    def create(self, params):
        """
        Create new items from a GeoJSON feature or feature collection. All
        GeoJSON features must contain a property named 'name' from which the
        name of each created item is taken.

        :param params: parameters to the API call, including 'folderId' and
                       'geoJSON'.
        :type params: dict[str, unknown]
        :returns: filtered fields of the created items with properties appended
                 to the 'meta' field and geospatial data appended to the 'geo'
                 field of each item.
        :rtype: list[dict[str, unknown]]
        :raise RestException: on malformed, forbidden, or unauthorized API call.
        """
        self.requireParams(('folderId', 'geoJSON'), params)

        try:
            geospatial = bson.json_util.loads(params['geoJSON'])
            GeoJSON.to_instance(geospatial, strict=True)
        except ValueError:
            raise RestException('Invalid GeoJSON passed in request body.')

        if geospatial['type'] == 'Feature':
            features = [geospatial]
        elif geospatial['type'] == 'FeatureCollection':
            features = geospatial['features']
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
                                        ' a period or begin with a dollar'
                                        ' sign.' % key)

            data.append({'name': name,
                         'description': description,
                         'metadata': properties,
                         'geometry': feature['geometry']})

        user = self.getCurrentUser()
        folder = self.model('folder').load(
            id=params['folderId'], user=user, level=AccessType.WRITE, exc=True)

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
    @describeRoute(
        Description('Search for an item by geospatial data.')
        .param('q', 'Search query as a JSON object.', required=True)
        .param('limit', 'Result set size limit (default=50).', required=False,
               dataType='integer')
        .param('offset', 'Offset into result set (default=0).', required=False,
               dataType='integer')
        .errorResponse()
    )
    def find(self, params):
        """
        Search for an item by geospatial data.

        :param params: parameters to the API call, including 'q'.
        :type params: dict[str, unknown]
        :returns: filtered fields of the matching items with geospatial data
                 appended to the 'geo' field of each item.
        :rtype: list[dict[str, unknown]]
        :raise RestException: on malformed API call.
        """
        self.requireParams(('q',), params)

        try:
            query = bson.json_util.loads(params['q'])
        except ValueError:
            raise RestException("Invalid JSON passed as 'q' parameter.")

        limit, offset, sort = self.getPagingParameters(params, 'lowerName')

        return self._find(query, limit, offset, sort)

    @access.public
    @describeRoute(
        Description('Search for items that intersects with a GeoJSON object.')
        .param('field', 'Name of field containing GeoJSON on which to search.',
               required=True)
        .param('geometry', 'Search query condition as a GeoJSON object.',
               required=True)
        .param('limit', 'Result set size limit (default=50).', required=False,
               dataType='integer')
        .param('offset', 'Offset into result set (default=0).', required=False,
               dataType='integer')
        .errorResponse()
    )
    def intersects(self, params):
        """
        Search for items that intersects with a GeoJSON object.

        :param params: parameters to the API call, including 'field' and
                       'geometry'.
        :type params: dict[str, unknown]
        :returns: filtered fields of the matching items with geospatial data
                 appended to the 'geo' field of each item.
        :rtype: list[dict[str, unknown]]
        :raise RestException: on malformed API call.
        """
        self.requireParams(('field', 'geometry'), params)

        try:
            geometry = bson.json_util.loads(params['geometry'])
            GeoJSON.to_instance(geometry, strict=True)
        except (TypeError, ValueError):
            raise RestException("Invalid GeoJSON passed as 'geometry'"
                                " parameter.")

        if params['field'][:3] == '%s.' % GEOSPATIAL_FIELD:
            field = params['field'].strip()
        else:
            field = '%s.%s' % (GEOSPATIAL_FIELD, params['field'].strip())

        query = {
            field: {
                '$geoIntersects': {
                    '$geometry': geometry
                }
            }
        }

        limit, offset, sort = self.getPagingParameters(params, 'lowerName')

        return self._find(query, limit, offset, sort)

    def _getGeometry(self, params):
        try:
            geometry = bson.json_util.loads(params['geometry'])
            GeoJSON.to_instance(geometry, strict=True)

            if geometry['type'] != 'Point':
                raise ValueError

            return geometry
        except (TypeError, ValueError):
            raise RestException("Invalid GeoJSON passed as 'geometry'"
                                " parameter.")

    @access.public
    @describeRoute(
        Description('Search for items that are in proximity to a GeoJSON'
                    ' point.')
        .param('field', 'Name of field containing GeoJSON on which to search.',
               required=True)
        .param('geometry', 'Search query condition as a GeoJSON point.',
               required=True)
        .param('maxDistance', 'Limits results to items that are at most this'
                              ' distance in meters from the GeoJSON point.',
               required=False, dataType='number')
        .param('minDistance', 'Limits results to items that are at least this'
                              ' distance in meters from the GeoJSON point.',
               required=False, dataType='number')
        .param('ensureIndex', 'Create a 2dsphere index on the field on which to'
                              ' search if one does not exist.', required=False,
               dataType='boolean')
        .param('limit', 'Result set size limit (default=50).', required=False,
               dataType='integer')
        .param('offset', 'Offset into result set (default=0).', required=False,
               dataType='integer')
        .errorResponse()
        .errorResponse('Field on which to search was not indexed.')
        .errorResponse('Index creation was denied.', 403)
        .notes("Field on which to search be indexed by a 2dsphere index."
               " Anonymous users may not use 'ensureIndex' to create such an"
               " index.")
    )
    def near(self, params):
        """
        Search for items that are in proximity to a GeoJSON point. The field on
        which to search must be indexed by a '2dsphere' index. Anonymous users
        may not use 'ensureIndex' to create such an index.

        :param params: parameters to the API call, including 'field' and
                       'geometry'.
        :type params: dict[str, unknown]
        :returns: filtered fields of the matching items with geospatial data
                 appended to the 'geo' field of each item.
        :rtype: list[dict[str, unknown]]
        :raise RestException: on malformed or forbidden API call.
        """
        self.requireParams(('field', 'geometry'), params)

        condition = {
            '$geometry': self._getGeometry(params)
        }

        for param in ('maxDistance', 'minDistance'):
            if param in params:
                try:
                    distance = float(params[param])

                    if distance < 0.0:
                        raise ValueError

                except ValueError:
                    raise RestException("Parameter '%s' must be a number." %
                                        param)

                condition['$'+param] = distance

        if params['field'][:3] == '%s.' % GEOSPATIAL_FIELD:
            field = params['field'].strip()
        else:
            field = '%s.%s' % (GEOSPATIAL_FIELD, params['field'].strip())

        if params.get('ensureIndex', False):
            user = self.getCurrentUser()

            if not user:
                raise RestException('Index creation denied.', 403)

            self.model('item').collection.create_index([(field, GEOSPHERE)])

        query = {
            field: {
                '$near': condition
            }
        }

        limit, offset, sort = self.getPagingParameters(params, 'lowerName')

        try:
            items = self._find(query, limit, offset, sort)
        except OperationFailure:
            raise RestException("Field '%s' must be indexed by a 2dsphere"
                                " index." % field)

        return items

    _RADIUS_OF_EARTH = 6378137.0  # average in meters

    @access.public
    @describeRoute(
        Description('Search for items that are entirely within either a GeoJSON'
                    ' polygon or a circular region.')
        .param('field', 'Name of field containing GeoJSON on which to search.',
               required=True)
        .param('geometry', 'Search query condition as a GeoJSON polygon.',
               required=False)
        .param('center', 'Center of search radius as a GeoJSON point.',
               required=False)
        .param('radius', 'Search radius in meters.', required=False,
               dataType='number')
        .param('limit', 'Result set size limit (default=50).', required=False,
               dataType='integer')
        .param('offset', 'Offset into result set (default=0).', required=False,
               dataType='integer')
        .errorResponse()
        .errorResponse('Field on which to search was not indexed.')
        .errorResponse('Index creation was denied.', 403)
        .notes("Either parameter 'geometry' or both parameters 'center' "
               " and 'radius' are required.")
    )
    def within(self, params):
        """
        Search for items that are entirely within either a GeoJSON polygon or a
        circular region. Either parameter 'geometry' or both parameters 'center'
        and 'radius' are required.

        :param params: parameters to the API call, including 'field' and either
                       'geometry' or both 'center' and 'radius'.
        :type params: dict[str, unknown]
        :returns: filtered fields of the matching items with geospatial data
                 appended to the 'geo' field of each item.
        :rtype: list[dict[str, unknown]]
        :raise RestException: on malformed API call.
        """
        self.requireParams(('field',), params)

        if 'geometry' in params:
            try:
                geometry = bson.json_util.loads(params['geometry'])
                GeoJSON.to_instance(geometry, strict=True)

                if geometry['type'] != 'Polygon':
                    raise ValueError
            except (TypeError, ValueError):
                raise RestException("Invalid GeoJSON passed as 'geometry'"
                                    " parameter.")

            condition = {
                '$geometry': geometry
            }

        elif 'center' in params and 'radius' in params:
            try:
                radius = float(params['radius']) / self._RADIUS_OF_EARTH

                if radius < 0.0:
                    raise ValueError
            except ValueError:
                raise RestException("Parameter 'radius' must be a number.")

            try:
                center = bson.json_util.loads(params['center'])
                GeoJSON.to_instance(center, strict=True)

                if center['type'] != 'Point':
                    raise ValueError
            except (TypeError, ValueError):
                raise RestException("Invalid GeoJSON passed as 'center'"
                                    " parameter.")

            condition = {
                '$centerSphere': [center['coordinates'], radius]
            }

        else:
            raise RestException("Either parameter 'geometry' or both parameters"
                                " 'center' and 'radius' are required.")

        if params['field'][:3] == '%s.' % GEOSPATIAL_FIELD:
            field = params['field'].strip()
        else:
            field = '%s.%s' % (GEOSPATIAL_FIELD, params['field'].strip())

        limit, offset, sort = self.getPagingParameters(params, 'lowerName')

        query = {
            field: {
                '$geoWithin': condition
            }
        }

        return self._find(query, limit, offset, sort)

    @access.public
    @loadmodel(model='item', level=AccessType.READ)
    @describeRoute(
        Description('Get an item and its geospatial data by ID.')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getGeospatial(self, item, params):
        """
        Get an item and its geospatial data by ID.

        :param item: item to return along with its geospatial data.
        :type item: dict[str, unknown]
        :param params: parameters to the API call, unused.
        :type params: dict[str, unknown]
        :returns: filtered fields of the item with geospatial data appended to
                 its 'geo' field.
        :rtype : dict[str, unknown]
        :raise RestException: on malformed or forbidden API call.
        """
        return self._filter(item)

    @access.user
    @loadmodel(model='item', level=AccessType.WRITE)
    @describeRoute(
        Description('Set geospatial fields on an item.')
        .notes('Set geospatial fields to null to delete them.')
        .param('id', 'The ID of the item.', paramType='path')
        .param('body', 'A JSON object containing the geospatial fields to add.',
               paramType='body')
        .errorResponse('ID was invalid.')
        .errorResponse('Invalid JSON was passed in request body.')
        .errorResponse('Geospatial key name was invalid.')
        .errorResponse('Geospatial field did not contain valid GeoJSON.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    def setGeospatial(self, item, params):
        """
        Set geospatial data on an item.

        :param item: item on which to set geospatial data.
        :type item: dict[str, unknown]
        :param params: parameters to the API call, unused.
        :type params: dict[str, unknown]
        :returns: filtered fields of the item with geospatial data appended to
                 its 'geo' field.
        :rtype : dict[str, unknown]
        :raise RestException: on malformed, forbidden, or unauthorized API call.
        """
        geospatial = self.getBodyJson()

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
        keys = [k for k, v in six.viewitems(item[GEOSPATIAL_FIELD])
                if v is None]

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
