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
from ..describe import Description
from ..rest import Resource, RestException, loadmodel
from girder.api import access


class Collection(Resource):
    """API Endpoint for collections."""
    def __init__(self):
        self.resourceName = 'collection'
        self.route('DELETE', (':id',), self.deleteCollection)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getCollection)
        self.route('GET', (':id', 'access'), self.getCollectionAccess)
        self.route('POST', (), self.createCollection)
        self.route('PUT', (':id',), self.updateCollection)
        self.route('PUT', (':id', 'access'), self.updateCollectionAccess)

    @access.public
    def find(self, params):
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')

        if 'text' in params:
            return [self.model('collection').filter(c, user) for c in
                    self.model('collection').textSearch(
                        params['text'], user=user, limit=limit, offset=offset)]

        cols = self.model('collection').list(user=user, offset=offset,
                                             limit=limit, sort=sort)
        return [self.model('collection').filter(c, user) for c in cols]
    find.description = (
        Description('List or search for collections.')
        .responseClass('Collection')
        .param('text', "Pass this to perform a text search for collections.",
               required=False)
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the result list by (default=name)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int'))

    @access.admin
    def createCollection(self, params):
        """Create a new collection. Requires global admin."""
        self.requireParams('name', params)

        user = self.getCurrentUser()

        public = self.boolParam('public', params, default=False)

        collection = self.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

        return self.model('collection').filter(collection)
    createCollection.description = (
        Description('Create a new collection.')
        .responseClass('Collection')
        .param('name', 'Name for the collection. Must be unique.')
        .param('description', 'Collection description.', required=False)
        .param('public', 'Whether the collection should be publicly visible.',
               dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator', 403))

    @access.public
    @loadmodel(model='collection', level=AccessType.READ)
    def getCollection(self, collection, params):
        return self.model('collection').filter(
            collection, self.getCurrentUser())
    getCollection.description = (
        Description('Get a collection by ID.')
        .responseClass('Collection')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the collection.', 403))

    @access.user
    @loadmodel(model='collection', level=AccessType.ADMIN)
    def getCollectionAccess(self, collection, params):
        return self.model('collection').getFullAccessList(collection)
    getCollectionAccess.description = (
        Description('Get the access control list for a collection.')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403))

    @access.user
    @loadmodel(model='collection', level=AccessType.ADMIN)
    def updateCollectionAccess(self, collection, params):
        self.requireParams('access', params)

        public = self.boolParam('public', params, default=False)
        self.model('collection').setPublic(collection, public)

        try:
            access = json.loads(params['access'])
            return self.model('collection').setAccessList(
                collection, access, save=True)
        except ValueError:
            raise RestException('The access parameter must be JSON.')
    updateCollectionAccess.description = (
        Description('Set the access control list for a collection.')
        .param('id', 'The ID of the collection.', paramType='path')
        .param('access', 'The access control list as JSON.')
        .param('public', 'Whether the collection should be publicly visible.',
               dataType='boolean')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403))

    @access.user
    @loadmodel(model='collection', level=AccessType.WRITE)
    def updateCollection(self, collection, params):
        collection['name'] = params.get('name', collection['name']).strip()
        collection['description'] = params.get(
            'description', collection['description']).strip()

        collection = self.model('collection').updateCollection(collection)
        return self.model('collection').filter(collection)
    updateCollection.description = (
        Description('Edit a collection by ID.')
        .responseClass('Collection')
        .param('id', 'The ID of the collection.', paramType='path')
        .param('name', 'Unique name for the collection.', required=False)
        .param('description', 'Collection description.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write permission denied on the collection.', 403))

    @access.user
    @loadmodel(model='collection', level=AccessType.ADMIN)
    def deleteCollection(self, collection, params):
        self.model('collection').remove(collection)
        return {'message': 'Deleted collection %s.' % collection['name']}
    deleteCollection.description = (
        Description('Delete a collection by ID.')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403))
