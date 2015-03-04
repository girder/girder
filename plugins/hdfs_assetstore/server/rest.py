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

from girder.api import access
from girder.api.describe import Description
from girder.api.rest import Resource, loadmodel
from snakebite.client import Client as HdfsClient


class HdfsAssetstoreResource(Resource):
    def __init__(self):
        self.resourceName = 'hdfs_assetstore'
        self.route('PUT', (':id', 'import'), self.importData)
        self.route('POST', (), self.createAssetstore)

    def _importData(self, parentType, parent, assetstore, client, path, ctx):
        ctx.update(message='Importing ' + path)
        for node in client.ls([path]):
            print node  # TODO import logic

    @access.admin
    @loadmodel(model='assetstore')
    def importData(self, assetstore, params):
        self.requireParams(('parentId', 'path'), params)

        parentType = params.get('parentType', 'folder')
        if parentType not in ('user', 'collection', 'folder'):
            raise RestException('Invalid parentType.')

        parent = self.model(parentType).load(params['parentId'], force=True,
                                             exc=True)

        progress = self.boolParam('progress', params, default=False)
        hdfsInfo = assetstore['hdfs']
        client = HdfsClient(
            host=assetstore['hdfs']['host'], port=assetstore['hdfs']['port'],
            use_trash=False)
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Importing data from HDFS') as ctx:
            self._importData(parentType, parent, assetstore, client, path, ctx)
    importData.description = (
        Description('Import a data hierarchy from an HDFS instance.')
        .notes('Only site administrators may use this endpoint.')
        .param('id', 'The ID of the assetstore representing the HDFS instance.',
                paramType='path')
        .param('parentId', 'The ID of the parent object in the Girder data '
               'hierarchy under which to import the files.')
        .param('parentType', 'The type of the parent object to import into.',
               enum=('folder', 'user', 'collection'), required=False)
        .param('progress', 'Whether to record progress on this operation ('
               'default=False)', required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    @access.admin
    def createAssetstore(self, params):
        pass  # TODO implement creation
    createAssetstore.description = (
        Description('Create a new HDFS assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('host', 'The HDFS hostname.')
        .param('port', 'The HDFS port for the name node.', dataType='integer')
        .param('path', 'Path in the HDFS under which to store new files.')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))
