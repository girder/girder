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

from . import features

from girder import events
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder.api.describe import Description
from girder.api.rest import Resource, RestException


class GeoJSON(Resource):

    def __init__(self):
        self.resourceName = 'geojson'

        self.route('GET', ('points',), self.points)

    def points(self, params):
        self.requireParams(('q',), params)
        limit, offset, sort = self.getPagingParameters(params, 'name')
        latitude = params.get('latitude', 'meta.latitude')
        longitude = params.get('longitude', 'meta.longitude')

        spec = {
            'type': 'point',
            'latitude': latitude,
            'longitude': longitude,
            'keys': ['meta', 'name', 'description', '_id'],
            'flatten': ['meta']
        }

        try:
            query = bson.json_util.loads(params['q'])
        except ValueError:  # pragma: no cover
            raise RestException('The query parameter must be a JSON object.')

        events.trigger('geojson.points', info={
            'spec': spec,
            'query': query
        })

        # make sure the lat/lon are whitelisted keys to prevent private
        # data leaking
        if spec['latitude'].split('.')[0] not in spec['keys'] or \
                spec['longitude'].split('.')[0] not in spec['keys']:
            raise RestException('Invalid latitude/longitude key.', code=402)

        coll = features.FeatureCollection(points=spec)

        item = ModelImporter().model('item')
        cursor = item.find(
            query,
            limit=0
        )

        cursor = item.filterResultsByPermission(
            cursor,
            user=self.getCurrentUser(),
            level=AccessType.READ,
            limit=limit,
            offset=offset
        )

        try:
            obj = coll(points=cursor)
        except features.GeoJSONException:
            raise RestException(
                'Could not assemble a geoJSON object from spec.',
                code=401
            )

        return obj

    points.description = (
        Description(
            'Returns an item query as a geoJSON point feature collection.'
        )
        .param('q', 'The search query as a JSON object.')
        .param(
            'longitude',
            'The location of the longitude in the object ' +
            '(default="meta.longitude").',
            required=False
        )
        .param(
            'latitude',
            'The location of the latitude in the object ' +
            '(default="meta.latitude").',
            required=False
        )
        .param(
            'limit',
            'Result set size limit (default=50).',
            required=False,
            dataType='int'
        )
        .param(
            'offset',
            'Offset into result set (default=0).',
            required=False,
            dataType='int'
        )
        .errorResponse()
        .errorResponse('Could not assemble geoJSON object.', 401)
        .errorResponse('Invalid latitude/longitude key.', 402)
    )


def load(info):
    info['apiRoot'].geojson = GeoJSON()
