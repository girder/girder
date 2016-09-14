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

from ..describe import Description, describeRoute
from ..rest import Resource, RestException, filtermodel, loadmodel, \
    setResponseHeader
from girder.utility import ziputil
from girder.constants import AccessType, TokenScope
from girder.api import access


class Item(Resource):

    def __init__(self):
        super(Item, self).__init__()
        self.resourceName = 'item'
        self.route('DELETE', (':id',), self.deleteItem)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getItem)
        self.route('GET', (':id', 'files'), self.getFiles)
        self.route('GET', (':id', 'download'), self.download)
        self.route('GET', (':id', 'rootpath'), self.rootpath)
        self.route('POST', (), self.createItem)
        self.route('PUT', (':id',), self.updateItem)
        self.route('POST', (':id', 'copy'), self.copyItem)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model='item')
    @describeRoute(
        Description('List or search for items.')
        .responseClass('Item', array=True)
        .param('folderId', "Pass this to list all items in a folder.",
               required=False)
        .param('text', "Pass this to perform a full text search for items.",
               required=False)
        .param('name', 'Pass to lookup an item by exact name match. Must '
               'pass folderId as well when using this.', required=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Read access was denied on the parent folder.', 403)
    )
    def find(self, params):
        """
        Get a list of items with given search parameters. Currently accepted
        search modes are:

        1. Searching by folderId, with optional additional filtering by the name
           field (exact match) or using full text search within a single parent
           folder. Pass a "name" parameter or "text" parameter to invoke these
           additional filters.
        2. Searching with full text search across all items in the system.
           Simply pass a "text" parameter for this mode.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lowerName')
        user = self.getCurrentUser()

        if 'folderId' in params:
            folder = self.model('folder').load(id=params['folderId'], user=user,
                                               level=AccessType.READ, exc=True)
            filters = {}
            if params.get('text'):
                filters['$text'] = {
                    '$search': params['text']
                }
            if params.get('name'):
                filters['name'] = params['name']

            return list(self.model('folder').childItems(
                folder=folder, limit=limit, offset=offset, sort=sort,
                filters=filters))
        elif 'text' in params:
            return list(self.model('item').textSearch(
                params['text'], user=user, limit=limit, offset=offset,
                sort=sort))
        else:
            raise RestException('Invalid search mode.')

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', level=AccessType.READ)
    @filtermodel(model='item')
    @describeRoute(
        Description('Get an item by ID.')
        .responseClass('Item')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getItem(self, item, params):
        return item

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='item')
    @describeRoute(
        Description('Create a new item.')
        .responseClass('Item')
        .param('folderId', 'The ID of the parent folder.')
        .param('name', 'Name for the item.')
        .param('description', "Description for the item.", required=False)
        .param('reuseExisting', 'Return existing item (by name) if it exists.',
               required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createItem(self, params):
        self.requireParams(('name', 'folderId'), params)

        user = self.getCurrentUser()
        name = params['name'].strip()
        description = params.get('description', '').strip()
        reuseExisting = params.get('reuseExisting', False)

        folder = self.model('folder').load(id=params['folderId'], user=user,
                                           level=AccessType.WRITE, exc=True)

        return self.model('item').createItem(
            folder=folder, name=name, creator=user, description=description,
            reuseExisting=reuseExisting)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', level=AccessType.WRITE)
    @filtermodel(model='item')
    @describeRoute(
        Description('Edit an item or move it to another folder.')
        .responseClass('Item')
        .param('id', 'The ID of the item.', paramType='path')
        .param('name', 'Name for the item.', required=False)
        .param('description', 'Description for the item.', required=False)
        .param('folderId', 'Pass this to move the item to a new folder.',
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item or folder.', 403)
    )
    def updateItem(self, item, params):
        item['name'] = params.get('name', item['name']).strip()
        item['description'] = params.get(
            'description', item['description']).strip()

        self.model('item').updateItem(item)

        if 'folderId' in params:
            folder = self.model('folder').load(
                params['folderId'], user=self.getCurrentUser(),
                level=AccessType.WRITE, exc=True)
            if folder['_id'] != item['folderId']:
                self.model('item').move(item, folder)

        return item

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', level=AccessType.WRITE)
    @filtermodel(model='item')
    @describeRoute(
        Description('Set metadata fields on an item.')
        .responseClass('Item')
        .notes('Set metadata fields to null in order to delete them.')
        .param('id', 'The ID of the item.', paramType='path')
        .param('body', 'A JSON object containing the metadata keys to add',
               paramType='body')
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the item.', 403)
    )
    def setMetadata(self, item, params):
        metadata = self.getBodyJson()

        # Make sure we let user know if we can't accept a metadata key
        for k in metadata:
            if not len(k):
                raise RestException('Key names must be at least one character '
                                    'long.')
            if '.' in k or k[0] == '$':
                raise RestException('The key name %s must not contain a period '
                                    'or begin with a dollar sign.' % k)

        return self.model('item').setMetadata(item, metadata)

    def _downloadMultifileItem(self, item, user):
        setResponseHeader('Content-Type', 'application/zip')
        setResponseHeader(
            'Content-Disposition',
            'attachment; filename="%s%s"' % (item['name'], '.zip'))

        def stream():
            zip = ziputil.ZipGenerator(item['name'])
            for (path, file) in self.model('item').fileList(item,
                                                            subpath=False):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', level=AccessType.READ)
    @filtermodel(model='file')
    @describeRoute(
        Description('Get the files within an item.')
        .responseClass('File', array=True)
        .param('id', 'The ID of the item.', paramType='path')
        .pagingParams(defaultSort='name')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def getFiles(self, item, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        return list(self.model('item').childFiles(
            item=item, limit=limit, offset=offset, sort=sort))

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', level=AccessType.READ)
    @describeRoute(
        Description('Download the contents of an item.')
        .param('id', 'The ID of the item.', paramType='path')
        .param('format', 'If unspecified, items with one file are downloaded '
               'as that file, and other items are downloaded as a zip '
               'archive.  If \'zip\', a zip archive is always sent.',
               required=False)
        .param('contentDisposition', 'Specify the Content-Disposition response '
               'header disposition-type value, only applied for single file '
               'items.', required=False, enum=['inline', 'attachment'],
               default='attachment')
        .param('extraParameters', 'Arbitrary data to send along with the '
               'download request, only applied for single file '
               'items.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def download(self, item, params):
        offset = int(params.get('offset', 0))
        user = self.getCurrentUser()
        files = list(self.model('item').childFiles(item=item, limit=2))
        format = params.get('format', '')
        if format not in (None, '', 'zip'):
            raise RestException('Unsupported format.')
        if len(files) == 1 and format != 'zip':
            contentDisp = params.get('contentDisposition')
            extraParameters = params.get('extraParameters')
            if (contentDisp is not None and
               contentDisp not in {'inline', 'attachment'}):
                raise RestException('Unallowed contentDisposition type "%s".' %
                                    contentDisp)
            return self.model('file').download(files[0], offset,
                                               contentDisposition=contentDisp,
                                               extraParameters=extraParameters)
        else:
            return self._downloadMultifileItem(item, user)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', level=AccessType.WRITE)
    @describeRoute(
        Description('Delete an item by ID.')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    def deleteItem(self, item, params):
        self.model('item').remove(item)
        return {'message': 'Deleted item %s.' % item['name']}

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='item', level=AccessType.READ)
    @describeRoute(
        Description('Get the path to the root of the item\'s hierarchy.')
        .param('id', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    def rootpath(self, item, params):
        return self.model('item').parentsToRoot(item, self.getCurrentUser())

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', level=AccessType.READ)
    @filtermodel(model='item')
    @describeRoute(
        Description('Copy an item.')
        .responseClass('Item')
        .param('id', 'The ID of the original item.', paramType='path')
        .param('folderId', 'The ID of the parent folder.', required=False)
        .param('name', 'Name for the new item.', required=False)
        .param('description', "Description for the new item.", required=False)
        .errorResponse(('A parameter was invalid.',
                        'ID was invalid.'))
        .errorResponse('Read access was denied on the original item.\n\n'
                       'Write access was denied on the parent folder.', 403)
    )
    def copyItem(self, item, params):
        """
        Copy an existing item to a new item.

        :param folderId: The _id of the parent folder for the new item.
        :type folderId: str
        :param name: The name of the item to create.
        :param description: Item description.
        """
        user = self.getCurrentUser()
        name = params.get('name', None)
        folderId = params.get('folderId', item['folderId'])
        folder = self.model('folder').load(
            id=folderId, user=user, level=AccessType.WRITE, exc=True)
        description = params.get('description', None)
        return self.model('item').copyItem(
            item, creator=user, name=name, folder=folder,
            description=description)
