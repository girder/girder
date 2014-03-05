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

from .docs import item_docs
from ..rest import Resource, RestException, loadmodel
from ...models.model_base import ValidationException
from ...utility import ziputil
from ...constants import AccessType


class Item(Resource):
    """API endpoint for items"""
    def __init__(self):
        self.route('DELETE', (':id',), self.deleteItem)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getItem)
        self.route('GET', (':id', 'files'), self.getFiles)
        self.route('GET', (':id', 'download'), self.download)
        self.route('POST', (), self.createItem)
        self.route('PUT', (':id',), self.updateItem)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)

    def _filter(self, item):
        """
        Filter an item document for display to the user.
        """
        return item

    def find(self, params):
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
        user = self.getCurrentUser()

        if 'text' in params:
            return self.model('item').textSearch(params['text'], {'name': 1})
            """return self.model('item').search(
                params['text'], user=user, offset=offset, limit=limit,
                sort=sort)"""
        elif 'folderId' in params:
            folder = self.model('folder').load(id=params['folderId'], user=user,
                                               level=AccessType.READ)

            return [item for item in self.model('folder').childItems(
                folder=folder, limit=limit, offset=offset, sort=sort)]
        else:
            raise RestException('Invalid search mode.')

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.READ)
    def getItem(self, item, params):
        return self._filter(item)

    def createItem(self, params):
        """
        Create a new item.

        :param folderId: The _id of the parent folder.
        :type folderId: str
        :param name: The name of the item to create.
        :param description: Item description.
        """
        self.requireParams(('name', 'folderId'), params)

        user = self.getCurrentUser()
        name = params['name'].strip()
        description = params.get('description', '').strip()

        folder = self.model('folder').load(id=params['folderId'], user=user,
                                           level=AccessType.WRITE)

        item = self.model('item').createItem(
            folder=folder, name=name, creator=user, description=description)

        return self._filter(item)

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.WRITE)
    def updateItem(self, item, params):
        user = self.getCurrentUser()
        item['name'] = params.get('name', item['name']).strip()
        item['description'] = params.get(
            'description', item['description']).strip()

        item = self.model('item').updateItem(item)
        return self._filter(item)

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.WRITE)
    def setMetadata(self, item, params):
        try:
            metadata = json.load(cherrypy.request.body)
        except ValueError:
            raise RestException('Invalid JSON passed in request body.')

        return self.model('item').setMetadata(item, metadata)

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

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.READ)
    def getFiles(self, item, params):
        """Get a page of files in an item."""
        limit, offset, sort = self.getPagingParameters(params, 'name')
        return [file for file in self.model('item').childFiles(
                item=item, limit=limit, offset=offset, sort=sort)]

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.READ)
    def download(self, item, params):
        """
        Defers to the underlying assetstore adapter to stream the file or
        file out.
        """
        offset = int(params.get('offset', 0))
        user = self.getCurrentUser()
        files = [file for file in self.model('item').childFiles(
                 item=item, limit=2)]

        if len(files) == 1:
            return self.model('file').download(files[0], offset)
        else:
            return self._downloadMultifileItem(item, user)

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.ADMIN)
    def deleteItem(self, item, params):
        """
        Delete an item and its contents.
        """
        self.model('item').remove(item)
        return {'message': 'Deleted item {}.'.format(item['name'])}
