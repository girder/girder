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

import json

from ..describe import Description, describeRoute
from ..rest import Resource, RestException, filtermodel, loadmodel, \
    setResponseHeader
from girder.api import access
from girder.constants import AccessType, TokenScope
from girder.models.model_base import AccessException
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Collection(Resource):
    """API Endpoint for collections."""
    def __init__(self):
        super(Collection, self).__init__()
        self.resourceName = 'collection'
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
    @filtermodel(model='collection')
    @describeRoute(
        Description('List or search for collections.')
        .responseClass('Collection', array=True)
        .param('text', "Pass this to perform a text search for collections.",
               required=False)
        .pagingParams(defaultSort='name')
    )
    def find(self, params):
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')

        if 'text' in params:
            return list(self.model('collection').textSearch(
                params['text'], user=user, limit=limit, offset=offset))

        return list(self.model('collection').list(
            user=user, offset=offset, limit=limit, sort=sort))

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='collection')
    @describeRoute(
        Description('Create a new collection.')
        .responseClass('Collection')
        .param('name', 'Name for the collection. Must be unique.')
        .param('description', 'Collection description.', required=False)
        .param('public', 'Whether the collection should be publicly visible.',
               dataType='boolean', default=False)
        .errorResponse()
        .errorResponse('You are not authorized to create collections.', 403)
    )
    def createCollection(self, params):
        self.requireParams('name', params)

        user = self.getCurrentUser()

        if not self.model('collection').hasCreatePrivilege(user):
            raise AccessException(
                'You are not authorized to create collections.')

        public = self.boolParam('public', params, default=False)

        return self.model('collection').createCollection(
            name=params['name'], description=params.get('description'),
            public=public, creator=user)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='collection', level=AccessType.READ)
    @filtermodel(model='collection')
    @describeRoute(
        Description('Get a collection by ID.')
        .responseClass('Collection')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the collection.', 403)
    )
    def getCollection(self, collection, params):
        return collection

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='collection', level=AccessType.READ)
    @describeRoute(
        Description('Get detailed information about a collection.')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse()
        .errorResponse('Read access was denied on the collection.', 403)
    )
    def getCollectionDetails(self, collection, params):
        return {
            'nFolders': self.model('collection').countFolders(
                collection, user=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='collection', level=AccessType.READ)
    @describeRoute(
        Description('Download an entire collection as a zip archive.')
        .param('id', 'The ID of the collection.', paramType='path')
        .param('mimeFilter', 'JSON list of MIME types to include.',
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the collection.', 403)
    )
    def downloadCollection(self, collection, params):
        setResponseHeader('Content-Type', 'application/zip')
        setResponseHeader(
            'Content-Disposition',
            'attachment; filename="%s%s"' % (collection['name'], '.zip'))

        user = self.getCurrentUser()
        mimeFilter = params.get('mimeFilter')
        if mimeFilter:
            try:
                mimeFilter = json.loads(mimeFilter)
                if not isinstance(mimeFilter, list):
                    raise ValueError()
            except ValueError:
                raise RestException('The mimeFilter must be a JSON list.')

        def stream():
            zip = ziputil.ZipGenerator(collection['name'])
            for (path, file) in self.model('collection').fileList(
                    collection, user=user, subpath=False,
                    mimeFilter=mimeFilter):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='collection', level=AccessType.ADMIN)
    @describeRoute(
        Description('Get the access control list for a collection.')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403)
    )
    def getCollectionAccess(self, collection, params):
        return self.model('collection').getFullAccessList(collection)

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='collection', level=AccessType.ADMIN)
    @filtermodel(model='collection', addFields={'access'})
    @describeRoute(
        Description('Set the access control list for a collection.')
        .param('id', 'The ID of the collection.', paramType='path')
        .param('access', 'The access control list as JSON.')
        .param('public', "Whether the collection should be publicly visible.",
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
    def updateCollectionAccess(self, collection, params):
        self.requireParams('access', params)
        user = self.getCurrentUser()

        public = self.boolParam('public', params)
        recurse = self.boolParam('recurse', params, default=False)
        progress = self.boolParam('progress', params, default=False) and recurse

        try:
            access = json.loads(params['access'])
        except ValueError:
            raise RestException('The access parameter must be JSON.')

        with ProgressContext(progress, user=user, title='Updating permissions',
                             message='Calculating progress...') as ctx:
            if progress:
                ctx.update(total=self.model('collection').subtreeCount(
                    collection, includeItems=False, user=user,
                    level=AccessType.ADMIN))
            return self.model('collection').setAccessList(
                collection, access, save=True, user=user, recurse=recurse,
                progress=ctx, setPublic=public)

    @access.user(scope=TokenScope.DATA_READ)
    @loadmodel(model='collection', level=AccessType.WRITE)
    @filtermodel(model='collection')
    @describeRoute(
        Description('Edit a collection by ID.')
        .responseClass('Collection')
        .param('id', 'The ID of the collection.', paramType='path')
        .param('name', 'Unique name for the collection.', required=False)
        .param('description', 'Collection description.', required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write permission denied on the collection.', 403)
    )
    def updateCollection(self, collection, params):
        collection['name'] = params.get('name', collection['name']).strip()
        collection['description'] = params.get(
            'description', collection['description']).strip()

        return self.model('collection').updateCollection(collection)

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='collection', level=AccessType.ADMIN)
    @describeRoute(
        Description('Delete a collection by ID.')
        .param('id', 'The ID of the collection.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin permission denied on the collection.', 403)
    )
    def deleteCollection(self, collection, params):
        self.model('collection').remove(collection)
        return {'message': 'Deleted collection %s.' % collection['name']}
