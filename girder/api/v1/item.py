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
import pymongo
import os

from .docs import item_docs
from ..rest import Resource, RestException
from ...models.model_base import ValidationException
from ...utility import ziputil
from ...constants import AccessType


class Item(Resource):
    """API endpoint for items"""

    def _filter(self, item):
        """
        Filter an item document for display to the user.
        """
        return item

    def find(self, user, params):
        """
        Get a list of items with given search parameters. Currently accepted
        search modes are:

        1. Searching by folderId.
        2. Searching with full text search.

        To search with full text search, pass the "text" parameter. To search
        by parent, (i.e. list child items in a folder) pass folderId. You can
        also pass limit, offset, sort, and sortdir paramters.

        :param text: Pass this to perform a full-text search of items.
        :param folderId: Get child items of a particular folder.
        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')

        if 'text' in params:
            return self.model('item').textSearch(params['text'],{'name':1})
            """return self.model('item').search(
                params['text'], user=user, offset=offset, limit=limit,
                sort=sort)"""
        elif 'folderId' in params:
            # Make sure user has read access on the folder
            folder = self.getObjectById(
                self.model('folder'), id=params['folderId'], user=user,
                checkAccess=True, level=AccessType.READ)

            return [item for item in self.model('folder').childItems(
                folder=folder, limit=limit, offset=offset, sort=sort)]
        else:
            raise RestException('Invalid search mode.')

    def createItem(self, user, params):
        """
        Create a new item.

        :param folderId: The _id of the parent folder.
        :type folderId: str
        :param name: The name of the item to create.
        :param description: Item description.
        """
        self.requireParams(['name', 'folderId'], params)

        name = params['name'].strip()
        description = params.get('description', '').strip()

        folder = self.getObjectById(
            self.model('folder'), id=params['folderId'], user=user,
            checkAccess=True, level=AccessType.WRITE)

        item = self.model('item').createItem(
            folder=folder, name=name, creator=user, description=description)

        return self._filter(item)

    def updateItem(self, id, user, params):
        item = self.getObjectById(
            self.model('item'), id=id, user=user, checkAccess=True,
            level=AccessType.WRITE)

        item['name'] = params.get('name', item['name']).strip()
        item['description'] = params.get(
            'description', item['description']).strip()

        item = self.model('item').updateItem(item)
        return self._filter(item)

    def addMetadata(self, id, user, params):
        if 'token' in params:
            del params['token']
        item = self.model('item').setMetadata(id, user, params)
        return item

    def _downloadMultifileItem(self, item, user):
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="{}{}"'.format(item['name'], '.zip')

        def stream():
            zip = ziputil.ZipGenerator(item['name'])
            for file in self.model('item').childFiles(item=item, limit=0):
                for data in zip.addFile(self.model('file')
                                            .download(file, headers=False),
                                        file['name']):
                    yield data
            yield zip.footer()
        return stream

    def download(self, user, params, itemId):
        """
        Defers to the underlying assetstore adapter to stream the file or
        file out.
        """
        offset = int(params.get('offset', 0))

        item = self.getObjectById(self.model('item'), id=itemId,
                                  checkAccess=True, user=user,
                                  level=AccessType.READ)  # Access Check
        files = [file for file in self.model('item').childFiles(item=item)]

        if len(files) == 1:
            return self.model('file').download(files[0], offset)
        else:
            return self._downloadMultifileItem(item, user)

    @Resource.endpoint
    def DELETE(self, path, params):
        """
        Delete an item.
        """
        if not path:
            raise RestException(
                'Path parameter should be the item ID to delete.')

        user = self.getCurrentUser()
        item = self.getObjectById(self.model('item'), user=user,
                                  id=path[0], checkAccess=True,
                                  level=AccessType.WRITE)

        self.model('item').remove(item)
        return {'message': 'Deleted item %s.' % item['name']}

    @Resource.endpoint
    def GET(self, path, params):
        user = self.getCurrentUser()
        if not path:
            return self.find(user, params)
        elif len(path) == 1:  # assume it's an item id
            item = self.getObjectById(self.model('item'), user=user,
                                      id=path[0], checkAccess=True,
                                      level=AccessType.READ)
            return self._filter(item)
        elif len(path) == 2 and path[1] == 'files':
            limit, offset, sort = self.getPagingParameters(params, 'name')
            item = self.getObjectById(self.model('item'), user=user,
                                      id=path[0], checkAccess=True,
                                      level=AccessType.READ)
            return [file for file in self.model('item').childFiles(
                item=item, limit=limit, offset=offset, sort=sort)]
        elif len(path) >= 2 and path[1] == 'download':
            return self.download(user, params, path[0])
        else:
            raise RestException('Unrecognized item GET endpoint.')

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to create an item.
        """
        return self.createItem(self.getCurrentUser(), params)

    @Resource.endpoint
    def PUT(self, path, params):
        """
        Use this endpoint to edit an item.
        """
        user = self.getCurrentUser()

        if not path:
            raise RestException(
                'Path parameter should be the item ID to edit.')
        elif len(path) == 1:
            return self.updateItem(path[0], user, params)
        elif len(path) == 2 and path[1] == 'metadata':
            return self.addMetadata(path[0], user, params)
