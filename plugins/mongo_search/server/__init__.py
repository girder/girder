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

from girder import events
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException
from girder.api import access


class ResourceExt(Resource):
    @access.public
    @describeRoute(
        Description('Run any search against a set of mongo collections.')
        .notes('Results will be filtered by permissions.')
        .param('type', 'The name of the collection to search, e.g. "item".')
        .param('q', 'The search query as a JSON object.')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .errorResponse()
    )
    def mongoSearch(self, params):
        self.requireParams(('type', 'q'), params)
        allowed = {
            'collection': ['_id', 'name', 'description'],
            'folder': ['_id', 'name', 'description'],
            'item': ['_id', 'name', 'description', 'folderId'],
            'user': ['_id', 'firstName', 'lastName', 'login']
        }
        limit, offset, sort = self.getPagingParameters(params, 'name')
        coll = params['type']

        events.trigger('mongo_search.allowed_collections', info=allowed)

        if coll not in allowed:
            raise RestException('Invalid resource type: %s' % coll)

        try:
            query = bson.json_util.loads(params['q'])
        except ValueError:
            raise RestException('The query parameter must be a JSON object.')

        model = ModelImporter().model(coll)
        if hasattr(model, 'filterResultsByPermission'):
            cursor = model.find(
                query, fields=allowed[coll] + ['public', 'access'])
            return list(model.filterResultsByPermission(
                cursor, user=self.getCurrentUser(), level=AccessType.READ,
                limit=limit, offset=offset, removeKeys=('public', 'access')))
        else:
            return list(model.find(query, fields=allowed[coll], limit=limit,
                                   offset=offset))


def load(info):
    ext = ResourceExt()
    info['apiRoot'].resource.route('GET', ('mongo_search',), ext.mongoSearch)
