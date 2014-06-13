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

from ..describe import Description
from ..rest import Resource, RestException, loadmodel
from ...models.model_base import ValidationException
from ...utility import ziputil
from ...constants import AccessType


class Item(Resource):
    """API endpoint for items"""
    def __init__(self):
        self.resourceName = 'item'
        self.route('DELETE', (':id',), self.deleteItem)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getItem)
        self.route('GET', (':id', 'files'), self.getFiles)
        self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (':id', 'rootpath'), self.rootpath)
        self.route('POST', (), self.createItem)
        self.route('PUT', (':id',), self.updateItem)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)

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
        :param sort: The field to sort by, default=lowerName.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lowerName')
        user = self.getCurrentUser()

        if 'text' in params:
            return self.model('item').textSearch(
                params['text'], {'name': 1}, user=user, limit=limit)
        elif 'folderId' in params:
            folder = self.model('folder').load(id=params['folderId'], user=user,
                                               level=AccessType.READ, exc=True)

            return [item for item in self.model('folder').childItems(
                folder=folder, limit=limit, offset=offset, sort=sort)]
        else:
            raise RestException('Invalid search mode.')
    find.description = (
        Description('Search for an item by certain properties.')
        .responseClass('Item')
        .param('folderId', "Pass this to list all items in a folder.",
               required=False)
        .param('text', "Pass this to perform a full text search for items.",
               required=False)
        .param('limit', "Result set size limit (default=50).",
               required=False, dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the item list by (default=name)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int')
        .errorResponse()
        .errorResponse('Read access was denied on the parent folder.', 403))

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.READ)
    def getItem(self, item, params):
        return self.model('item').filter(item)
    getItem.description = (
        Description('Get an item by ID.')
        .responseClass('Item')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403))

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
                                           level=AccessType.WRITE, exc=True)

        item = self.model('item').createItem(
            folder=folder, name=name, creator=user, description=description)

        return self.model('item').filter(item)
    createItem.description = (
        Description('Create a new item.')
        .responseClass('Item')
        .param('folderId', 'The ID of the parent folder.')
        .param('name', 'Name for the item.')
        .param('description', "Description for the item.", required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403))

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.WRITE)
    def updateItem(self, item, params):
        user = self.getCurrentUser()
        item['name'] = params.get('name', item['name']).strip()
        item['description'] = params.get(
            'description', item['description']).strip()

        item = self.model('item').updateItem(item)
        return self.model('item').filter(item)
    updateItem.description = (
        Description('Edit an item by ID.')
        .responseClass('Item')
        .param('id', 'The ID of the item.', paramType='path')
        .param('name', 'Name for the item.', required=False)
        .param('description', 'Description for the item', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403))

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.WRITE)
    def setMetadata(self, item, params):
        try:
            metadata = json.load(cherrypy.request.body)
        except ValueError:
            raise RestException('Invalid JSON passed in request body.')

        # Make sure we let user know if we can't accept one of their metadata
        # keys
        for k in metadata:
            if '.' in k or k[0] == '$':
                raise RestException('The key name ' + k + ' must not ' +
                                    'contain a period or begin with a ' +
                                    'dollar sign.')

        return self.model('item').setMetadata(item, metadata)
    setMetadata.description = (
        Description('Set metadata fields on an item.')
        .responseClass('Item')
        .notes('Set metadata fields to null in order to delete them.')
        .param('id', 'The ID of the item.', paramType='path')
        .param('body', 'A JSON object containing the metadata keys to add',
               paramType='body')
        .errorResponse('ID was invalid.')
        .errorResponse('Invalid JSON passed in request body.')
        .errorResponse('Metadata key name was invalid.')
        .errorResponse('Write access was denied for the item.', 403))

    def _downloadMultifileItem(self, item, user):
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] =\
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
    getFiles.description = (
        Description('Get the files within an item.')
        .responseClass('File')
        .param('id', 'The ID of the item.', paramType='path')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the result list by (default=name)",
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403))

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
    download.description = (
        Description('Download the contents of an item.')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403))

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.ADMIN)
    def deleteItem(self, item, params):
        """
        Delete an item and its contents.
        """
        self.model('item').remove(item)
        return {'message': 'Deleted item {}.'.format(item['name'])}
    deleteItem.description = (
        Description('Delete an item by ID.')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the item.', 403))

    @loadmodel(map={'id': 'item'}, model='item', level=AccessType.READ)
    def rootpath(self, item, params):
        """
        Get the path to the root of the item's parent hierarchy.
        """
        return self.model('item').parentsToRoot(item, self.getCurrentUser())
    rootpath.description = (
        Description('Get the path to the root of the item\'s hierarchy')
        .param('id', 'The ID of the item', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403))
