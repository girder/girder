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

import posixpath

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel, RestException
from girder.utility.progress import ProgressContext
from snakebite.client import Client as HdfsClient
from snakebite.errors import FileNotFoundException


class HdfsAssetstoreResource(Resource):
    def __init__(self):
        super(HdfsAssetstoreResource, self).__init__()
        self.resourceName = 'hdfs_assetstore'
        self.route('PUT', (':id', 'import'), self.importData)

        self.folderModel = self.model('folder')  # Save to avoid many lookups
        self.itemModel = self.model('item')
        self.fileModel = self.model('file')

    def _importFile(self, parent, name, user, assetstore, node):
        item = self.itemModel.findOne({
            'folderId': parent['_id'],
            'name': name
        })
        if item is None:
            item = self.itemModel.createItem(
                name=name, creator=user, folder=parent)

        file = self.fileModel.findOne({
            'name': name,
            'itemId': item['_id']
        })
        if file is None:
            file = self.fileModel.createFile(
                creator=user, item=item, name=name, size=node['length'],
                assetstore=assetstore, mimeType=None, saveFile=False)

        file['hdfs'] = {
            'imported': True,
            'path': node['path']
        }
        self.fileModel.save(file)

    def _importData(self, parentType, parent, assetstore, client, path, ctx,
                    user):
        for node in client.ls([path]):
            ctx.update(message='Importing ' + node['path'])
            name = posixpath.basename(node['path'])

            if node['file_type'] == 'd':
                folder = self.folderModel.findOne({
                    'parentId': parent['_id'],
                    'name': name,
                    'parentCollection': parentType
                })
                if folder is None:
                    folder = self.folderModel.createFolder(
                        parent, name, parentType=parentType, creator=user)

                self._importData('folder', folder, assetstore, client,
                                 node['path'], ctx, user)
            elif node['file_type'] == 'f' and parentType == 'folder':
                self._importFile(parent, name, user, assetstore, node)

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Import a data hierarchy from an HDFS instance.')
        .notes('Only site administrators may use this endpoint.')
        .param('id', 'The ID of the assetstore representing the HDFS instance.',
               paramType='path')
        .param('parentId', 'The ID of the parent object in the Girder data '
               'hierarchy under which to import the files.')
        .param('parentType', 'The type of the parent object to import into.',
               enum=('folder', 'user', 'collection'), required=False)
        .param('path', 'Root of the directory structure (relative to the root '
               'of the HDFS) to import.')
        .param('progress', 'Whether to record progress on this operation ('
               'default=False)', required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def importData(self, assetstore, params):
        self.requireParams(('parentId', 'path'), params)

        user = self.getCurrentUser()
        parentType = params.get('parentType', 'folder')
        if parentType not in ('user', 'collection', 'folder'):
            raise RestException('Invalid parentType.')

        parent = self.model(parentType).load(params['parentId'], force=True,
                                             exc=True)

        progress = self.boolParam('progress', params, default=False)
        client = HdfsClient(
            host=assetstore['hdfs']['host'], port=assetstore['hdfs']['port'],
            use_trash=False)
        path = params['path']

        with ProgressContext(progress, user=user,
                             title='Importing data from HDFS') as ctx:
            try:
                self._importData(
                    parentType, parent, assetstore, client, path, ctx, user)
            except FileNotFoundException:
                raise RestException('File not found: %s.' % path)
