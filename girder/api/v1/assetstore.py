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

from ..describe import Description
from ..rest import Resource, RestException, loadmodel
from girder.constants import AssetstoreType
from girder.api import access


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

    @access.admin
    def find(self, params):
        """
        Get a list of assetstores.

        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')

        return list(self.model('assetstore').list(
            offset=offset, limit=limit, sort=sort))
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

    @access.admin
    def createAssetstore(self, params):
        """Create a new assetstore."""
        self.requireParams(('type', 'name'), params)

        assetstoreType = int(params['type'])

        if assetstoreType == AssetstoreType.FILESYSTEM:
            self.requireParams('root', params)
            return self.model('assetstore').createFilesystemAssetstore(
                name=params['name'], root=params['root'])
        elif assetstoreType == AssetstoreType.GRIDFS:
            self.requireParams('db', params)
            return self.model('assetstore').createGridFsAssetstore(
                name=params['name'], db=params['db'],
                mongohost=params.get('mongohost', None),
                replicaset=params.get('replicaset', None))
        elif assetstoreType == AssetstoreType.S3:
            self.requireParams(('bucket', 'accessKeyId', 'secret'), params)
            return self.model('assetstore').createS3Assetstore(
                name=params['name'], bucket=params['bucket'],
                prefix=params.get('prefix', ''), secret=params['secret'],
                accessKeyId=params.get('accessKeyId'),
                service=params.get('service', ''))
        else:
            raise RestException('Invalid type parameter')
    createAssetstore.description = (
        Description('Create a new assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('type', 'Type of the assetstore.', dataType='integer')
        .param('root', 'Root path on disk (for filesystem type).',
               required=False)
        .param('db', 'Database name (for GridFS type)', required=False)
        .param('mongohost', 'Mongo host URI (for GridFS type)', required=False)
        .param('replicaset', 'Replica set name (for GridFS type)',
               required=False)
        .param('bucket', 'The S3 bucket to store data in (for S3 type).',
               required=False)
        .param('prefix', 'Optional path prefix within the bucket under which '
               'files will be stored (for S3 type).', required=False)
        .param('accessKeyId', 'The AWS access key ID to use for authentication '
               '(for S3 type).', required=False)
        .param('secret', 'The AWS secret key to use for authentication (for '
               'S3 type).', required=False)
        .param('service', 'The S3 service host (for S3 type).  Default is '
               's3.amazonaws.com.  This can be used to specify a protocol and '
               'port as well using the form '
               '[http[s]://](host domain)[:(port)].  Do not include the '
               'bucket name here.', required=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    @access.admin
    @loadmodel(model='assetstore')
    def updateAssetstore(self, assetstore, params):
        self.requireParams(('name', 'current'), params)

        assetstore['name'] = params['name'].strip()
        assetstore['current'] = params['current'].lower() == 'true'

        if assetstore['type'] == AssetstoreType.FILESYSTEM:
            self.requireParams('root', params)
            assetstore['root'] = params['root']
        elif assetstore['type'] == AssetstoreType.GRIDFS:
            self.requireParams('db', params)
            assetstore['db'] = params['db']
            if 'mongohost' in params:
                assetstore['mongohost'] = params['mongohost']
            if 'replicaset' in params:
                assetstore['replicaset'] = params['replicaset']
        elif assetstore['type'] == AssetstoreType.S3:
            self.requireParams(('bucket', 'accessKeyId', 'secret'), params)
            assetstore['bucket'] = params['bucket']
            assetstore['prefix'] = params.get('prefix', '')
            assetstore['accessKeyId'] = params['accessKeyId']
            assetstore['secret'] = params['secret']
            assetstore['service'] = params.get('service', '')
        return self.model('assetstore').save(assetstore)
    updateAssetstore.description = (
        Description('Update an existing assetstore.')
        .responseClass('Assetstore')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .param('name', 'Unique name for the assetstore')
        .param('root', 'Root path on disk (for Filesystem type)',
               required=False)
        .param('db', 'Database name (for GridFS type)', required=False)
        .param('mongohost', 'Mongo host URI (for GridFS type)', required=False)
        .param('replicaset', 'Replica set name (for GridFS type)',
               required=False)
        .param('bucket', 'The S3 bucket to store data in (for S3 type).',
               required=False)
        .param('prefix', 'Optional path prefix within the bucket under which '
               'files will be stored (for S3 type).', required=False)
        .param('accessKeyId', 'The AWS access key ID to use for authentication '
               '(for S3 type).', required=False)
        .param('secret', 'The AWS secret key to use for authentication (for '
               'S3 type).', required=False)
        .param('service', 'The S3 service host (for S3 type).  Default is '
               's3.amazonaws.com.  This can be used to specify a protocol and '
               'port as well using the form '
               '[http[s]://](host domain)[:(port)].  Do not include the '
               'bucket name here.', required=False)
        .param('current', 'Whether this is the current assetstore',
               dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403))

    @access.admin
    @loadmodel(model='assetstore')
    def deleteAssetstore(self, assetstore, params):
        self.model('assetstore').remove(assetstore)
        return {'message': 'Deleted assetstore {}.'.format(assetstore['name'])}
    deleteAssetstore.description = (
        Description('Delete an assetstore.')
        .notes('This will fail if there are any files in the assetstore.')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .errorResponse()
        .errorResponse('The assetstore is not empty.')
        .errorResponse('You are not an administrator.', 403))
