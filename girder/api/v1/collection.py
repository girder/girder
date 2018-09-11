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
from ..rest import Resource, filtermodel, setResponseHeader, setContentDisposition
from girder.api import access
from girder.constants import AccessType, TokenScope
from girder.models.collection import Collection as CollectionModel
from girder.exceptions import AccessException
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Collection(Resource):
    """API Endpoint for collections."""
    def __init__(self):
        super(Collection, self).__init__()
        self.resourceName = 'collection'
        self._model = CollectionModel()

        self.route('DELETE', (':id',), self.deleteCollection)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getCollection)
        self.route('GET', (':id', 'details'), self.getCollectionDetails)
        self.route('GET', (':id', 'download'), self.downloadCollection)
        self.route('GET', (':id', 'access'), self.getCollectionAccess)
        self.route('POST', (), self.createCollection)
        self.route('PUT', (':id',), self.updateCollection)
        self.route('PUT', (':id', 'access'), self.updateCollectionAccess)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=CollectionModel)
    @autoDescribeRoute(
        Description('List or search for collections.')
        .responseClass('Collection', array=True)
        .param('text', 'Pass this to perform a text search for collections.', required=False)
        .pagingParams(defaultSort='name')
    )
    def find(self, text, limit, offset, sort):
        user = self.getCurrentUser()

        if text is not None:
            return self._model.textSearch(text, user=user, limit=limit, offset=offset)

        return self._model.list(user=user, offset=offset, limit=limit, sort=sort)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=CollectionModel)
    @autoDescribeRoute(
        Description('Create a new collection.')
        .responseClass('Collection')
        .param('name', 'Name for the collection. Must be unique.')
        .param('description', 'Collection description.', required=False)
        .param('public', 'Whether the collection should be publicly visible.',
               required=False, dataType='boolean', default=False)
        .errorResponse()
        .errorResponse('You are not authorized to create collections.', 403)
    )
    def createCollection(self, name, description, public):
        user = self.getCurrentUser()

        if not self._model.hasCreatePrivilege(user):
            raise AccessException('You are not authorized to create collections.')

        return self._model.createCollection(
            name=name, description=description, public=public, creator=user)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=CollectionModel)
    @autoDescribeRoute(
        Description('Get a collection by ID.')
        .responseClass('Collection')
        .modelParam('id', model=CollectionModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the collection.', 403)
    )
    def getCollection(self, collection):
        return collection

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get detailed information about a collection.')
        .modelParam('id', model=CollectionModel, level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the collection.', 403)
    )
    def getCollectionDetails(self, collection):
        return {
            'nFolders': self._model.countFolders(
                collection, user=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Download an entire collection as a zip archive.')
        .modelParam('id', model=CollectionModel, level=AccessType.READ)
        .jsonParam('mimeFilter', 'JSON list of MIME types to include.', requireArray=True,
                   required=False)
        .produces('application/zip')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the collection.', 403)
    )
    def downloadCollection(self, collection, mimeFilter):
        setResponseHeader('Content-Type', 'application/zip')
        setContentDisposition(collection['name'] + '.zip')

        def stream():
            zip = ziputil.ZipGenerator(collection['name'])
            for (path, file) in self._model.fileList(
                    collection, user=self.getCurrentUser(), subpath=False, mimeFilter=mimeFilter):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get the access control list for a collection.')
        .modelParam('id', model=CollectionModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403)
    )
    def getCollectionAccess(self, collection):
        return self._model.getFullAccessList(collection)

    @access.user(scope=TokenScope.DATA_OWN)
    @filtermodel(model=CollectionModel, addFields={'access'})
    @autoDescribeRoute(
        Description('Set the access control list for a collection.')
        .modelParam('id', model=CollectionModel, level=AccessType.ADMIN)
        .jsonParam('access', 'The access control list as JSON.', requireObject=True)
        .jsonParam('publicFlags', 'List of public access flags to set on the collection.',
                   required=False, requireArray=True)
        .param('public', 'Whether the collection should be publicly visible.',
               dataType='boolean', required=False)
        .param('recurse', 'Whether the policies should be applied to all '
               'folders under this collection as well.', dataType='boolean',
               default=False, required=False)
        .param('progress', 'If recurse is set to True, this controls whether '
               'progress notifications will be sent.', dataType='boolean',
               default=False, required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403)
    )
    def updateCollectionAccess(self, collection, access, public, recurse, progress, publicFlags):
        user = self.getCurrentUser()
        progress = progress and recurse

        with ProgressContext(progress, user=user, title='Updating permissions',
                             message='Calculating progress...') as ctx:
            if progress:
                ctx.update(total=self._model.subtreeCount(
                    collection, includeItems=False, user=user, level=AccessType.ADMIN))
            return self._model.setAccessList(
                collection, access, save=True, user=user, recurse=recurse,
                progress=ctx, setPublic=public, publicFlags=publicFlags)

    @access.user(scope=TokenScope.DATA_READ)
    @filtermodel(model=CollectionModel)
    @autoDescribeRoute(
        Description('Edit a collection by ID.')
        .responseClass('Collection')
        .modelParam('id', model=CollectionModel, level=AccessType.WRITE)
        .param('name', 'Unique name for the collection.', required=False, strip=True)
        .param('description', 'Collection description.', required=False, strip=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Write permission denied on the collection.', 403)
    )
    def updateCollection(self, collection, name, description):
        if name is not None:
            collection['name'] = name
        if description is not None:
            collection['description'] = description

        return self._model.updateCollection(collection)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Delete a collection by ID.')
        .modelParam('id', model=CollectionModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403)
    )
    def deleteCollection(self, collection):
        self._model.remove(collection)
        return {'message': 'Deleted collection %s.' % collection['name']}
