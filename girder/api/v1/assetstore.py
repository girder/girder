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

from .. import describe
from ..describe import Description
from ..rest import Resource, RestException, loadmodel
from girder.constants import AssetstoreType


class Assetstore(Resource):
    """
    API Endpoint for managing assetstores. Requires admin privileges.
    """
    def __init__(self):
        self.resourceName = 'assetstore'
        self.route('GET', (), self.find)
        self.route('POST', (), self.createAssetstore)
        self.route('PUT', (':id',), self.updateAssetstore)
        self.route('DELETE', (':id',), self.deleteAssetstore)

    def find(self, params):
        """
        Get a list of assetstores.

        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        self.requireAdmin(self.getCurrentUser())
        limit, offset, sort = self.getPagingParameters(params, 'name')

        return self.model('assetstore').list(
            offset=offset, limit=limit, sort=sort)
    find.description = (
        Description('List assetstores.')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='integer')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='integer')
        .param('sort', "Field to sort the assetstore list by (default=name)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='integer')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    def createAssetstore(self, params):
        """Create a new assetstore."""
        self.requireAdmin(self.getCurrentUser())
        self.requireParams(('type', 'name'), params)

        assetstoreType = int(params['type'])

        if assetstoreType == AssetstoreType.FILESYSTEM:
            self.requireParams(('root',), params)
            return self.model('assetstore').createFilesystemAssetstore(
                name=params['name'], root=params['root'])
        elif assetstoreType == AssetstoreType.GRIDFS:
            self.requireParams(('db',), params)
            return self.model('assetstore').createGridFsAssetstore(
                name=params['name'], db=params['db'])
        elif assetstoreType == AssetstoreType.S3:
            return self.model('assetstore').createS3Assetstore(
                name=params['name'])
        else:
            raise RestException('Invalid type parameter')
    createAssetstore.description = (
        Description('Create a new assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('type', 'Type of the assetstore.', dataType='integer')
        .param('root', 'Root path on disk (for filesystem type)',
               required=False)
        .param('db', 'Database name (for GridFS type)', required=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    @loadmodel(map={'id': 'assetstore'}, model='assetstore')
    def updateAssetstore(self, assetstore, params):
        self.requireAdmin(self.getCurrentUser())
        self.requireParams(('name', 'current'), params)

        assetstore['name'] = params['name'].strip()
        assetstore['current'] = params['current'].lower() == 'true'

        if assetstore['type'] == AssetstoreType.FILESYSTEM:
            self.requireParams(('root',), params)
            assetstore['root'] = params['root']
        elif assetstore['type'] == AssetstoreType.GRIDFS:
            self.requireParams(('db',), params)
            assetstore['db'] = params['db']

        return self.model('assetstore').save(assetstore)
    updateAssetstore.description = (
        Description('Update an existing assetstore.')
        .responseClass('Assetstore')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .param('name', 'Unique name for the assetstore')
        .param('root', 'Root path on disk (for Filesystem type)',
               required=False)
        .param('db', 'Database name (for GridFS type)', required=False)
        .param('current', 'Whether this is the current assetstore',
               dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    @loadmodel(map={'id': 'assetstore'}, model='assetstore')
    def deleteAssetstore(self, assetstore, params):
        self.requireAdmin(self.getCurrentUser())
        self.model('assetstore').remove(assetstore)
        return {'message': 'Deleted assetstore {}.'.format(assetstore['name'])}
    deleteAssetstore.description = (
        Description('Delete an assetstore.')
        .notes('This will fail if there are any files in the assetstore.')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .errorResponse()
        .errorResponse('The assetstore is not empty.')
        .errorResponse('You are not an administrator.', 403))
