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

import cherrypy
import json

from ...constants import AccessType
from ..rest import Resource, RestException
from .docs import collection_docs


class Collection(Resource):
    """API Endpoint for collections."""

    def _filter(self, user):
        """
        Helper to filter the collection model.
        """
        return self.filterDocument(
            user, allow=['_id', 'name', 'description', 'public',
            'created', 'updated', 'size'])

    def find(self, user, params):
        """
        Get a list of collections. You can pass a "text" parameter to filter the
        collections by a full text search string.

        :param [text]: Full text search.
        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        (limit, offset, sort) = self.getPagingParameters(params, 'name')

        return [self._filter(c) for c in self.model('collection').search(
                text=params.get('text'), user=user,
                offset=offset, limit=limit, sort=sort)]

    def createCollection(self, user, params):
        self.requireParams(['name'], params)

        public = params.get('public', 'false').lower() == 'true'

        collection = self.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

        return self._filter(collection)

    def updateCollection(self, path, user, params):
        collection = self.getObjectById(
            self.model('collection'), id=path[0], user=user, checkAccess=True,
            level=AccessType.ADMIN)
        modifiedCollection = dict(collection.items() + params.items())
        updatedCollection = self.model('collection').updateCollection(
            modifiedCollection)
        return self._filter(updatedCollection)

    @Resource.endpoint
    def DELETE(self, path, params):
        """
        Delete a collection.
        """
        if not path:
            raise RestException(
                'Path parameter should be the collection ID to delete.')

        user = self.getCurrentUser()
        collection = self.getObjectById(
            self.model('collection'), id=path[0], user=user, checkAccess=True,
            level=AccessType.ADMIN)

        self.model('collection').remove(collection)
        return {'message': 'Deleted collection %s.' % collection['name']}

    @Resource.endpoint
    def GET(self, path, params):
        user = self.getCurrentUser()
        if not path:
            return self.find(user, params)
        else:  # assume it's a collection id
            return self._filter(self.getObjectById(
                self.model('collection'), id=path[0], user=user,
                checkAccess=True))

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to create a new collection. Requires global
        administrative access.
        """
        user = self.getCurrentUser()
        self.requireAdmin(user)

        return self.createCollection(user, params)

    @Resource.endpoint
    def PUT(self, path, params):
        """
        Use this endpoint to edit a collection. Requires admin access
        to that collection.
        """
        if not path:
            raise RestException(
                'Path parameter should be the collection ID to edit.')

        user = self.getCurrentUser()
        return self.updateCollection(path, user, params)
