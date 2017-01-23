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

from ..describe import Description, autoDescribeRoute
from ..rest import Resource, RestException
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
    @autoDescribeRoute(
        Description('Get information about an assetstore.')
        .modelParam('id', model='assetstore')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstore(self, assetstore, params):
        self.model('assetstore').addComputedInfo(assetstore)
        return assetstore

    @access.admin
    @autoDescribeRoute(
        Description('List assetstores.')
        .pagingParams(defaultSort='name')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def find(self, limit, offset, sort, params):
        return list(self.model('assetstore').list(offset=offset, limit=limit, sort=sort))

    @access.admin
    @autoDescribeRoute(
        Description('Create a new assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('type', 'Type of the assetstore.', dataType='integer')
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
               'files will be stored (for S3 type).', required=False, default='')
        .param('accessKeyId', 'The AWS access key ID to use for authentication '
               '(for S3 type).', required=False)
        .param('secret', 'The AWS secret key to use for authentication (for '
               'S3 type).', required=False)
        .param('service', 'The S3 service host (for S3 type).  Default is '
               's3.amazonaws.com.  This can be used to specify a protocol and '
               'port as well using the form [http[s]://](host domain)[:(port)]. '
               'Do not include the bucket name here.', required=False, default='')
        .param('readOnly', 'If this assetstore is read-only, set this to true.',
               required=False, dataType='boolean', default=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def createAssetstore(self, name, type, root, perms, db, mongohost, replicaset, bucket,
                         prefix, accessKeyId, secret, service, readOnly, params):
        if type == AssetstoreType.FILESYSTEM:
            self.requireParams({'root': root})
            return self.model('assetstore').createFilesystemAssetstore(
                name=name, root=root, perms=perms)
        elif type == AssetstoreType.GRIDFS:
            self.requireParams({'db': db})
            return self.model('assetstore').createGridFsAssetstore(
                name=name, db=db, mongohost=mongohost, replicaset=replicaset)
        elif type == AssetstoreType.S3:
            self.requireParams({'bucket': bucket})
            return self.model('assetstore').createS3Assetstore(
                name=name, bucket=bucket, prefix=prefix, secret=secret,
                accessKeyId=accessKeyId, service=service, readOnly=readOnly)
        else:
            raise RestException('Invalid type parameter')

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Import existing data into an assetstore.')
        .notes('This does not move or copy the existing data, it just creates '
               'references to it in the Girder data hierarchy. Deleting '
               'those references will not delete the underlying data. This '
               'operation is currently only supported for S3 assetstores.')
        .modelParam('id', model='assetstore')
        .param('importPath', 'Root path within the underlying storage system '
               'to import.', required=False)
        .param('destinationId', 'ID of a folder, collection, or user in Girder '
               'under which the data will be imported.')
        .param('destinationType', 'Type of the destination resource.',
               enum=('folder', 'collection', 'user'))
        .param('progress', 'Whether to record progress on the import.',
               dataType='boolean', default=False, required=False)
        .param('leafFoldersAsItems', 'Whether folders containing only files should be '
               'imported as items.', dataType='boolean', required=False, default=False)
        .param('fileIncludeRegex', 'If set, only filenames matching this regular '
               'expression will be imported.', required=False)
        .param('fileExcludeRegex', 'If set, only filenames that do not match this regular '
               'expression will be imported. If a file matches both the include and exclude regex, '
               'it will be excluded.', required=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def importData(self, assetstore, importPath, destinationId, destinationType, progress,
                   leafFoldersAsItems, fileIncludeRegex, fileExcludeRegex, params):
        user = self.getCurrentUser()
        parent = self.model(destinationType).load(
            destinationId, user=user, level=AccessType.ADMIN, exc=True)

        with ProgressContext(progress, user=user, title='Importing data') as ctx:
            return self.model('assetstore').importData(
                assetstore, parent=parent, parentType=destinationType, params={
                    'fileIncludeRegex': fileIncludeRegex,
                    'fileExcludeRegex': fileExcludeRegex,
                    'importPath': importPath,
                }, progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems)

    @access.admin
    @autoDescribeRoute(
        Description('Update an existing assetstore.')
        .responseClass('Assetstore')
        .modelParam('id', model='assetstore')
        .param('name', 'Unique name for the assetstore.', strip=True)
        .param('root', 'Root path on disk (for Filesystem type)', required=False)
        .param('perms', 'File creation permissions (for Filesystem type)', required=False)
        .param('db', 'Database name (for GridFS type)', required=False)
        .param('mongohost', 'Mongo host URI (for GridFS type)', required=False)
        .param('replicaset', 'Replica set name (for GridFS type)', required=False)
        .param('bucket', 'The S3 bucket to store data in (for S3 type).', required=False)
        .param('prefix', 'Optional path prefix within the bucket under which '
               'files will be stored (for S3 type).', required=False, default='')
        .param('accessKeyId', 'The AWS access key ID to use for authentication '
               '(for S3 type).', required=False)
        .param('secret', 'The AWS secret key to use for authentication (for '
               'S3 type).', required=False)
        .param('service', 'The S3 service host (for S3 type).  Default is '
               's3.amazonaws.com.  This can be used to specify a protocol and '
               'port as well using the form [http[s]://](host domain)[:(port)]. '
               'Do not include the bucket name here.', required=False, default='')
        .param('readOnly', 'If this assetstore is read-only, set this to true.',
               required=False, dataType='boolean')
        .param('current', 'Whether this is the current assetstore', dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def updateAssetstore(self, assetstore, name, root, perms, db, mongohost, replicaset, bucket,
                         prefix, accessKeyId, secret, service, readOnly, current, params):
        assetstore['name'] = name
        assetstore['current'] = current

        if assetstore['type'] == AssetstoreType.FILESYSTEM:
            self.requireParams({'root': root})
            assetstore['root'] = root
            if perms is not None:
                assetstore['perms'] = perms
        elif assetstore['type'] == AssetstoreType.GRIDFS:
            self.requireParams({'db': db})
            assetstore['db'] = db
            if mongohost is not None:
                assetstore['mongohost'] = mongohost
            if replicaset is not None:
                assetstore['replicaset'] = replicaset
        elif assetstore['type'] == AssetstoreType.S3:
            self.requireParams({
                'bucket': bucket,
                'accessKeyId': accessKeyId,
                'secret': secret
            })
            assetstore['bucket'] = bucket
            assetstore['prefix'] = prefix
            assetstore['accessKeyId'] = accessKeyId
            assetstore['secret'] = secret
            assetstore['service'] = service
            if readOnly is not None:
                assetstore['readOnly'] = readOnly
        else:
            event = events.trigger('assetstore.update', info={
                'assetstore': assetstore,
                'params': dict(
                    name=name, current=current, readOnly=readOnly, root=root, perms=perms,
                    db=db, mongohost=mongohost, replicaset=replicaset, bucket=bucket,
                    prefix=prefix, accessKeyId=accessKeyId, secret=secret, service=service,
                    **params
                )
            })
            if event.defaultPrevented:
                return
        return self.model('assetstore').save(assetstore)

    @access.admin
    @autoDescribeRoute(
        Description('Delete an assetstore.')
        .notes('This will fail if there are any files in the assetstore.')
        .modelParam('id', model='assetstore')
        .errorResponse(('A parameter was invalid.',
                        'The assetstore is not empty.'))
        .errorResponse('You are not an administrator.', 403)
    )
    def deleteAssetstore(self, assetstore, params):
        self.model('assetstore').remove(assetstore)
        return {'message': 'Deleted assetstore %s.' % assetstore['name']}

    @access.admin
    @autoDescribeRoute(
        Description('Get a list of files controlled by an assetstore.')
        .modelParam('id', model='assetstore')
        .pagingParams(defaultSort='_id')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstoreFiles(self, assetstore, limit, offset, sort, params):
        return list(self.model('file').find(
            query={'assetstoreId': assetstore['_id']},
            offset=offset, limit=limit, sort=sort))
