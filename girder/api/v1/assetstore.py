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
from ..rest import Resource, RestException, loadmodel
from girder import events
from girder.constants import AccessType, AssetstoreType, TokenScope
from girder.api import access
from girder.utility.progress import ProgressContext


class Assetstore(Resource):
    """
    API Endpoint for managing assetstores. Requires admin privileges.
    """
    def __init__(self):
        super(Assetstore, self).__init__()
        self.resourceName = 'assetstore'
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getAssetstore)
        self.route('POST', (), self.createAssetstore)
        self.route('POST', (':id', 'import'), self.importData)
        self.route('PUT', (':id',), self.updateAssetstore)
        self.route('DELETE', (':id',), self.deleteAssetstore)
        self.route('GET', (':id', 'files'), self.getAssetstoreFiles)

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Get information about an assetstore.')
        .param('id', 'The assetstore ID.', paramType='path')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstore(self, assetstore, params):
        self.model('assetstore').addComputedInfo(assetstore)
        return assetstore

    @access.admin
    @describeRoute(
        Description('List assetstores.')
        .pagingParams(defaultSort='name')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
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

    @access.admin
    @describeRoute(
        Description('Create a new assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('type', 'Type of the assetstore.')
        .param('root', 'Root path on disk (for filesystem type).',
               required=False)
        .param('perms', 'File creation permissions (for filesystem type).',
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
        .param('readOnly', 'If this assetstore is read-only, set this to true.',
               required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def createAssetstore(self, params):
        """Create a new assetstore."""
        self.requireParams(('type', 'name'), params)

        assetstoreType = int(params['type'])

        if assetstoreType == AssetstoreType.FILESYSTEM:
            self.requireParams('root', params)
            perms = params.get('perms', None)
            return self.model('assetstore').createFilesystemAssetstore(
                name=params['name'], root=params['root'], perms=perms)
        elif assetstoreType == AssetstoreType.GRIDFS:
            self.requireParams('db', params)
            return self.model('assetstore').createGridFsAssetstore(
                name=params['name'], db=params['db'],
                mongohost=params.get('mongohost', None),
                replicaset=params.get('replicaset', None))
        elif assetstoreType == AssetstoreType.S3:
            self.requireParams(('bucket'), params)
            return self.model('assetstore').createS3Assetstore(
                name=params['name'], bucket=params['bucket'],
                prefix=params.get('prefix', ''), secret=params.get('secret'),
                accessKeyId=params.get('accessKeyId'),
                service=params.get('service', ''),
                readOnly=self.boolParam('readOnly', params, default=False))
        else:
            raise RestException('Invalid type parameter')

    @access.admin(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Import existing data into an assetstore.')
        .notes('This does not move or copy the existing data, it just creates '
               'references to it in the Girder data hierarchy. Deleting '
               'those references will not delete the underlying data. This '
               'operation is currently only supported for S3 assetstores.')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .param('importPath', 'Root path within the underlying storage system '
               'to import.', required=False)
        .param('destinationId', 'ID of a folder, collection, or user in Girder '
               'under which the data will be imported.')
        .param('destinationType', 'Type of the destination resource.',
               enum=('folder', 'collection', 'user'))
        .param('progress', 'Whether to record progress on the import.',
               dataType='boolean', default=False, required=False)
        .param('fileIncludeRegex', 'If set, only filenames matching this regular '
               'expression will be imported.', required=False)
        .param('fileExcludeRegex', 'If set, only filenames that do not match this regular '
               'expression will be imported. If a file matches both the include and exclude regex, '
               'it will be excluded.', required=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def importData(self, assetstore, params):
        self.requireParams(('destinationId', 'destinationType'), params)

        parentType = params.pop('destinationType')
        if parentType not in ('folder', 'collection', 'user'):
            raise RestException('The destinationType must be user, folder, or collection.')

        user = self.getCurrentUser()
        parent = self.model(parentType).load(
            params.pop('destinationId'), user=user, level=AccessType.ADMIN, exc=True)

        progress = self.boolParam('progress', params, default=False)
        leafFoldersAsItems = self.boolParam('leafFoldersAsItems', params, default=False)
        with ProgressContext(progress, user=user, title='Importing data') as ctx:
            return self.model('assetstore').importData(
                assetstore, parent=parent, parentType=parentType, params=params,
                progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems)

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Update an existing assetstore.')
        .responseClass('Assetstore')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .param('name', 'Unique name for the assetstore')
        .param('root', 'Root path on disk (for Filesystem type)',
               required=False)
        .param('perms', 'File creation permissions (for Filesystem type)',
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
        .param('readOnly', 'If this assetstore is read-only, set this to true.',
               required=False, dataType='boolean')
        .param('current', 'Whether this is the current assetstore',
               dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def updateAssetstore(self, assetstore, params):
        self.requireParams(('name', 'current'), params)

        assetstore['name'] = params['name'].strip()
        assetstore['current'] = params['current'].lower() == 'true'

        if assetstore['type'] == AssetstoreType.FILESYSTEM:
            self.requireParams('root', params)
            assetstore['root'] = params['root']
            if 'perms' in params:
                assetstore['perms'] = params['perms']
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
            assetstore['readOnly'] = self.boolParam(
                'readOnly', params, default=assetstore.get('readOnly'))
        else:
            event = events.trigger('assetstore.update', info={
                'assetstore': assetstore,
                'params': params
            })
            if event.defaultPrevented:
                return
        return self.model('assetstore').save(assetstore)

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Delete an assetstore.')
        .notes('This will fail if there are any files in the assetstore.')
        .param('id', 'The ID of the assetstore.', paramType='path')
        .errorResponse(('A parameter was invalid.',
                        'The assetstore is not empty.'))
        .errorResponse('You are not an administrator.', 403)
    )
    def deleteAssetstore(self, assetstore, params):
        self.model('assetstore').remove(assetstore)
        return {'message': 'Deleted assetstore %s.' % assetstore['name']}

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Get a list of files controlled by an assetstore.')
        .param('id', 'The assetstore ID.', paramType='path')
        .pagingParams(defaultSort='_id')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstoreFiles(self, assetstore, params):
        limit, offset, sort = self.getPagingParameters(params, '_id')
        return list(self.model('file').find(
            query={'assetstoreId': assetstore['_id']},
            offset=offset, limit=limit, sort=sort))
