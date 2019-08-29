# -*- coding: utf-8 -*-
from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from girder import events
from girder.constants import AccessType, AssetstoreType, TokenScope
from girder.exceptions import RestException
from girder.api import access
from girder.models.assetstore import Assetstore as AssetstoreModel
from girder.models.file import File
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext
from girder.utility.s3_assetstore_adapter import DEFAULT_REGION


class Assetstore(Resource):
    """
    API Endpoint for managing assetstores. Requires admin privileges.
    """

    def __init__(self):
        super(Assetstore, self).__init__()
        self.resourceName = 'assetstore'
        self._model = AssetstoreModel()

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
        .modelParam('id', model=AssetstoreModel)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstore(self, assetstore):
        self._model.addComputedInfo(assetstore)
        return assetstore

    @access.admin
    @autoDescribeRoute(
        Description('List assetstores.')
        .pagingParams(defaultSort='name')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def find(self, limit, offset, sort):
        return self._model.list(offset=offset, limit=limit, sort=sort)

    @access.admin
    @autoDescribeRoute(
        Description('Create a new assetstore.')
        .responseClass('Assetstore')
        .notes('You must be an administrator to call this.')
        .param('name', 'Unique name for the assetstore.')
        .param('type', 'Type of the assetstore.', dataType='integer')
        .param('root', 'Root path on disk (for filesystem type).', required=False)
        .param('perms', 'File creation permissions (for filesystem type).', required=False)
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
               required=False, dataType='boolean', default=False)
        .param('region', 'The AWS region to which the S3 bucket belongs.', required=False,
               default=DEFAULT_REGION)
        .param('inferCredentials', 'The credentials for connecting to S3 will be inferred '
               'by Boto rather than explicitly passed. Inferring credentials will '
               'ignore accessKeyId and secret.', dataType='boolean', required=False)
        .param('serverSideEncryption', 'Whether to use S3 SSE to encrypt the objects uploaded to '
               'this bucket (for S3 type).', dataType='boolean', required=False, default=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def createAssetstore(self, name, type, root, perms, db, mongohost, replicaset, bucket,
                         prefix, accessKeyId, secret, service, readOnly, region, inferCredentials,
                         serverSideEncryption):
        if type == AssetstoreType.FILESYSTEM:
            self.requireParams({'root': root})
            return self._model.createFilesystemAssetstore(
                name=name, root=root, perms=perms)
        elif type == AssetstoreType.GRIDFS:
            self.requireParams({'db': db})
            return self._model.createGridFsAssetstore(
                name=name, db=db, mongohost=mongohost, replicaset=replicaset)
        elif type == AssetstoreType.S3:
            self.requireParams({'bucket': bucket})
            return self._model.createS3Assetstore(
                name=name, bucket=bucket, prefix=prefix, secret=secret,
                accessKeyId=accessKeyId, service=service, readOnly=readOnly, region=region,
                inferCredentials=inferCredentials, serverSideEncryption=serverSideEncryption)
        else:
            raise RestException('Invalid type parameter')

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Import existing data into an assetstore.')
        .notes('This does not move or copy the existing data, it just creates '
               'references to it in the Girder data hierarchy. Deleting '
               'those references will not delete the underlying data. This '
               'operation is currently only supported for S3 assetstores.')
        .modelParam('id', model=AssetstoreModel)
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
                   leafFoldersAsItems, fileIncludeRegex, fileExcludeRegex):
        user = self.getCurrentUser()
        parent = ModelImporter.model(destinationType).load(
            destinationId, user=user, level=AccessType.ADMIN, exc=True)

        with ProgressContext(progress, user=user, title='Importing data') as ctx:
            return self._model.importData(
                assetstore, parent=parent, parentType=destinationType, params={
                    'fileIncludeRegex': fileIncludeRegex,
                    'fileExcludeRegex': fileExcludeRegex,
                    'importPath': importPath,
                }, progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems)

    @access.admin
    @autoDescribeRoute(
        Description('Update an existing assetstore.')
        .responseClass('Assetstore')
        .modelParam('id', model=AssetstoreModel)
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
        .param('region', 'The AWS region to which the S3 bucket belongs.', required=False,
               default=DEFAULT_REGION)
        .param('current', 'Whether this is the current assetstore', dataType='boolean')
        .param('inferCredentials', 'The credentials for connecting to S3 will be inferred '
               'by Boto rather than explicitly passed. Inferring credentials will '
               'ignore accessKeyId and secret.', dataType='boolean', required=False)
        .param('serverSideEncryption', 'Whether to use S3 SSE to encrypt the objects uploaded to '
               'this bucket (for S3 type).', dataType='boolean', required=False, default=False)
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def updateAssetstore(self, assetstore, name, root, perms, db, mongohost, replicaset,
                         bucket, prefix, accessKeyId, secret, service, readOnly, region, current,
                         inferCredentials, serverSideEncryption, params):
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
                'bucket': bucket
            })
            assetstore['bucket'] = bucket
            assetstore['prefix'] = prefix
            assetstore['accessKeyId'] = accessKeyId
            assetstore['secret'] = secret
            assetstore['service'] = service
            assetstore['region'] = region
            assetstore['inferCredentials'] = inferCredentials
            assetstore['serverSideEncryption'] = serverSideEncryption
            if readOnly is not None:
                assetstore['readOnly'] = readOnly
        else:
            event = events.trigger('assetstore.update', info={
                'assetstore': assetstore,
                'params': dict(
                    name=name, current=current, readOnly=readOnly, root=root, perms=perms,
                    db=db, mongohost=mongohost, replicaset=replicaset, bucket=bucket,
                    prefix=prefix, accessKeyId=accessKeyId, secret=secret, service=service,
                    region=region, **params
                )
            })
            if event.defaultPrevented:
                return
        return self._model.save(assetstore)

    @access.admin
    @autoDescribeRoute(
        Description('Delete an assetstore.')
        .notes('This will fail if there are any files in the assetstore.')
        .modelParam('id', model=AssetstoreModel)
        .errorResponse(('A parameter was invalid.',
                        'The assetstore is not empty.'))
        .errorResponse('You are not an administrator.', 403)
    )
    def deleteAssetstore(self, assetstore):
        self._model.remove(assetstore)
        return {'message': 'Deleted assetstore %s.' % assetstore['name']}

    @access.admin
    @autoDescribeRoute(
        Description('Get a list of files controlled by an assetstore.')
        .modelParam('id', model=AssetstoreModel)
        .pagingParams(defaultSort='_id')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403)
    )
    def getAssetstoreFiles(self, assetstore, limit, offset, sort):
        return File().find(
            query={'assetstoreId': assetstore['_id']}, offset=offset, limit=limit, sort=sort)
