#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import json

from ...constants import AccessType
from ..rest import Resource, RestException, loadmodel
from .docs import collection_docs


class Collection(Resource):
    """API Endpoint for collections."""
    def __init__(self):
        self.route('DELETE', (':id',), self.deleteCollection)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getCollection)
        self.route('GET', (':id', 'access'), self.getCollectionAccess)
        self.route('POST', (), self.createCollection)
        self.route('PUT', (':id',), self.updateCollection)
        self.route('PUT', (':id', 'access'), self.updateCollectionAccess)

    def _filter(self, collection):
        """Helper to filter the collection model."""
        filtered = self.filterDocument(
            collection, allow=('_id', 'name', 'description', 'public',
                               'created', 'updated', 'size'))

        filtered['_accessLevel'] = self.model('collection').getAccessLevel(
            collection, self.getCurrentUser())

        return filtered

    def find(self, params):
        """
        Get a list of collections. You can pass a "text" parameter to filter the
        collections by a full text search string.

        :param [text]: Full text search.
        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')

        return [self._filter(c) for c in self.model('collection').list(
                user=user, offset=offset, limit=limit, sort=sort)]

    def createCollection(self, params):
        """Create a new collection. Requires global admin."""
        self.requireParams(['name'], params)

        user = self.getCurrentUser()
        self.requireAdmin(user)

        public = params.get('public', 'false').lower() == 'true'

        collection = self.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

        return self._filter(collection)

    @loadmodel(map={'id': 'coll'}, model='collection', level=AccessType.READ)
    def getCollection(self, coll, params):
        return self._filter(coll)

    @loadmodel(map={'id': 'coll'}, model='collection', level=AccessType.ADMIN)
    def getCollectionAccess(self, coll, params):
        return self.model('collection').getFullAccessList(coll)

    @loadmodel(map={'id': 'coll'}, model='collection', level=AccessType.ADMIN)
    def updateCollectionAccess(self, coll, params):
        self.requireParams(('access',), params)

        public = params.get('public', '').lower() == 'true'
        self.model('collection').setPublic(coll, public)

        try:
            access = json.loads(params['access'])
            return self.model('collection').setAccessList(
                coll, access, save=True)
        except ValueError:
            raise RestException('The access parameter must be JSON.')

    @loadmodel(map={'id': 'coll'}, model='collection', level=AccessType.WRITE)
    def updateCollection(self, coll, params):
        coll['name'] = params.get('name', coll['name']).strip()
        coll['description'] = params.get(
            'description', coll['description']).strip()

        coll = self.model('collection').updateCollection(coll)
        return self._filter(coll)

    @loadmodel(map={'id': 'coll'}, model='collection', level=AccessType.ADMIN)
    def deleteCollection(self, coll, params):
        self.model('collection').remove(coll)
        return {'message': 'Deleted collection %s.' % coll['name']}
