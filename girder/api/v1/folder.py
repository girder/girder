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
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Folder(Resource):
    """API Endpoint for folders."""

    def __init__(self):
        super(Folder, self).__init__()
        self.resourceName = 'folder'
        self.route('DELETE', (':id',), self.deleteFolder)
        self.route('DELETE', (':id', 'contents'), self.deleteContents)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getFolder)
        self.route('GET', (':id', 'details'), self.getFolderDetails)
        self.route('GET', (':id', 'access'), self.getFolderAccess)
        self.route('GET', (':id', 'download'), self.downloadFolder)
        self.route('POST', (), self.createFolder)
        self.route('PUT', (':id',), self.updateFolder)
        self.route('PUT', (':id', 'access'), self.updateFolderAccess)
        self.route('POST', (':id', 'copy'), self.copyFolder)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Search for folders by certain properties.')
        .responseClass('Folder', array=True)
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', "The ID of the folder's parent.", required=False)
        .param('text', 'Pass to perform a text search.', required=False)
        .param('name', 'Pass to lookup a folder by exact name match. Must '
               'pass parentType and parentId as well when using this.',
               required=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Read access was denied on the parent resource.', 403)
    )
    def find(self, params):
        """
        Get a list of folders with given search parameters. Currently accepted
        search modes are:

        1. Searching by parentId and parentType, with optional additional
           filtering by the name field (exact match) or using full text search
           within a single parent folder. Pass a "name" parameter or "text"
           parameter to invoke these additional filters.
        2. Searching with full text search across all folders in the system.
           Simply pass a "text" parameter for this mode.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lowerName')
        user = self.getCurrentUser()

        if 'parentId' in params and 'parentType' in params:
            parentType = params['parentType'].lower()
            if parentType not in ('collection', 'folder', 'user'):
                raise RestException('The parentType must be user, collection,'
                                    ' or folder.')

            parent = self.model(parentType).load(
                id=params['parentId'], user=user, level=AccessType.READ,
                exc=True)

            filters = {}
            if params.get('text'):
                filters['$text'] = {
                    '$search': params['text']
                }
            if params.get('name'):
                filters['name'] = params['name']

            return list(self.model('folder').childFolders(
                parentType=parentType, parent=parent, user=user,
                offset=offset, limit=limit, sort=sort, filters=filters))
        elif 'text' in params:
            return list(self.model('folder').textSearch(
                params['text'], user=user, limit=limit, offset=offset,
                sort=sort))
        else:
            raise RestException('Invalid search mode.')

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='folder', level=AccessType.READ)
    @describeRoute(
        Description('Get detailed information about a folder.')
        .param('id', 'The ID of the folder.', paramType='path')
        .errorResponse()
        .errorResponse('Read access was denied on the folder.', 403)
    )
    def getFolderDetails(self, folder, params):
        return {
            'nItems': self.model('folder').countItems(folder),
            'nFolders': self.model('folder').countFolders(
                folder, user=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='folder', level=AccessType.READ)
    @describeRoute(
        Description('Download an entire folder as a zip archive.')
        .param('id', 'The ID of the folder.', paramType='path')
        .param('mimeFilter', 'JSON list of MIME types to include.',
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the folder.', 403)
    )
    def downloadFolder(self, folder, params):
        """
        Returns a generator function that will be used to stream out a zip
        file containing this folder's contents, filtered by permissions.
        """
        setResponseHeader('Content-Type', 'application/zip')
        setResponseHeader(
            'Content-Disposition',
            'attachment; filename="%s%s"' % (folder['name'], '.zip'))

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
            zip = ziputil.ZipGenerator(folder['name'])
            for (path, file) in self.model('folder').fileList(
                    folder, user=user, subpath=False, mimeFilter=mimeFilter):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='folder', level=AccessType.WRITE)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Update a folder or move it into a new parent.')
        .responseClass('Folder')
        .param('id', 'The ID of the folder.', paramType='path')
        .param('name', 'Name of the folder.', required=False)
        .param('description', 'Description for the folder.', required=False)
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', 'Parent ID for the new parent of this folder.',
               required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new '
                       'parent object.', 403)
    )
    def updateFolder(self, folder, params):
        user = self.getCurrentUser()
        folder['name'] = params.get('name', folder['name']).strip()
        folder['description'] = params.get(
            'description', folder['description']).strip()

        folder = self.model('folder').updateFolder(folder)

        if 'parentType' in params and 'parentId' in params:
            parentType = params['parentType'].lower()
            if parentType not in ('user', 'collection', 'folder'):
                raise RestException('Invalid parentType.')

            parent = self.model(parentType).load(
                params['parentId'], level=AccessType.WRITE, user=user, exc=True)
            if (parentType, parent['_id']) !=\
               (folder['parentCollection'], folder['parentId']):
                folder = self.model('folder').move(folder, parent, parentType)

        return folder

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='folder', level=AccessType.ADMIN)
    @filtermodel(model='folder', addFields={'access'})
    @describeRoute(
        Description('Update the access control list for a folder.')
        .param('id', 'The ID of the folder.', paramType='path')
        .param('access', 'The JSON-encoded access control list.')
        .param('public', "Whether the folder should be publicly visible.",
               dataType='boolean', required=False)
        .param('recurse', 'Whether the policies should be applied to all '
               'subfolders under this folder as well.', dataType='boolean',
               default=False, required=False)
        .param('progress', 'If recurse is set to True, this controls whether '
               'progress notifications will be sent.', dataType='boolean',
               default=False, required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the folder.', 403)
    )
    def updateFolderAccess(self, folder, params):
        self.requireParams('access', params)
        user = self.getCurrentUser()

        public = self.boolParam('public', params)
        recurse = self.boolParam('recurse', params, default=False)
        progress = self.boolParam('progress', params, default=False) and recurse

        access = self.getParamJson('access', params, default={})
        publicFlags = self.getParamJson('publicFlags', params, default=None)

        with ProgressContext(progress, user=user, title='Updating permissions',
                             message='Calculating progress...') as ctx:
            if progress:
                ctx.update(total=self.model('folder').subtreeCount(
                    folder, includeItems=False, user=user,
                    level=AccessType.ADMIN))
            return self.model('folder').setAccessList(
                folder, access, save=True, recurse=recurse, user=user,
                progress=ctx, setPublic=public, publicFlags=publicFlags)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Create a new folder.')
        .responseClass('Folder')
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', "The ID of the folder's parent.")
        .param('name', "Name of the folder.")
        .param('description', "Description for the folder.", required=False)
        .param('public', "Whether the folder should be publicly visible. By "
               "default, inherits the value from parent folder, or in the "
               "case of user or collection parentType, defaults to False.",
               required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('Write access was denied on the parent', 403)
    )
    def createFolder(self, params):
        """
        Create a new folder.

        :param parentId: The _id of the parent folder.
        :type parentId: str
        :param parentType: The type of the parent of this folder.
        :type parentType: str - 'user', 'collection', or 'folder'
        :param name: The name of the folder to create.
        :param description: Folder description.
        :param public: Public read access flag.
        :type public: bool
        """
        self.requireParams(('name', 'parentId'), params)

        user = self.getCurrentUser()
        parentType = params.get('parentType', 'folder').lower()
        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = self.boolParam('public', params, default=None)

        if parentType not in ('folder', 'user', 'collection'):
            raise RestException('Set parentType to collection, folder, '
                                'or user.')

        model = self.model(parentType)

        parent = model.load(id=params['parentId'], user=user,
                            level=AccessType.WRITE, exc=True)

        return self.model('folder').createFolder(
            parent=parent, name=name, parentType=parentType, creator=user,
            description=description, public=public)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='folder', level=AccessType.READ)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Get a folder by ID.')
        .responseClass('Folder')
        .param('id', 'The ID of the folder.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the folder.', 403)
    )
    def getFolder(self, folder, params):
        return folder

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='folder', level=AccessType.ADMIN)
    @describeRoute(
        Description('Get the access control list for a folder.')
        .responseClass('Folder')
        .param('id', 'The ID of the folder.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the folder.', 403)
    )
    def getFolderAccess(self, folder, params):
        return self.model('folder').getFullAccessList(folder)

    @access.user(scope=TokenScope.DATA_OWN)
    @loadmodel(model='folder', level=AccessType.ADMIN)
    @describeRoute(
        Description('Delete a folder by ID.')
        .param('id', 'The ID of the folder.', paramType='path')
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the folder.', 403)
    )
    def deleteFolder(self, folder, params):
        progress = self.boolParam('progress', params, default=False)
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Deleting folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self.model('folder').subtreeCount(folder))
            self.model('folder').remove(folder, progress=ctx)
        return {'message': 'Deleted folder %s.' % folder['name']}

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='folder', level=AccessType.WRITE)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Set metadata fields on an folder.')
        .responseClass('Folder')
        .notes('Set metadata fields to null in order to delete them.')
        .param('id', 'The ID of the folder.', paramType='path')
        .param('body', 'A JSON object containing the metadata keys to add',
               paramType='body')
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the folder.', 403)
    )
    def setMetadata(self, folder, params):
        metadata = self.getBodyJson()

        # Make sure we let user know if we can't accept a metadata key
        for k in metadata:
            if '.' in k or k[0] == '$':
                raise RestException('The key name %s must not contain a '
                                    'period or begin with a dollar sign.' % k)

        return self.model('folder').setMetadata(folder, metadata)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='folder', level=AccessType.READ)
    @filtermodel(model='folder')
    @describeRoute(
        Description('Copy a folder.')
        .responseClass('Folder')
        .param('id', 'The ID of the original folder.', paramType='path')
        .param('parentType', "Type of the new folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', 'The ID of the parent document.', required=False)
        .param('name', 'Name for the new folder.', required=False)
        .param('description', "Description for the new folder.", required=False)
        .param('public', "Whether the folder should be publicly visible. By "
               "default, inherits the value from parent folder, or in the case "
               "of user or collection parentType, defaults to False. If "
               "'original', use the value of the original folder.",
               required=False, enum=[True, False, 'original'])
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse(('A parameter was invalid.',
                        'ID was invalid.'))
        .errorResponse('Read access was denied on the original folder.\n\n'
                       'Write access was denied on the parent.', 403)
    )
    def copyFolder(self, folder, params):
        user = self.getCurrentUser()
        parentType = params.get('parentType', folder['parentCollection'])
        if 'parentId' in params:
            parentId = params.get('parentId', folder['parentId'])
            parent = self.model(parentType).load(
                id=parentId, user=user, level=AccessType.WRITE, exc=True)
        else:
            parent = None
        name = params.get('name', None)
        description = params.get('description', None)
        public = params.get('public', None)
        progress = self.boolParam('progress', params, default=False)
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Copying folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self.model('folder').subtreeCount(folder))
            return self.model('folder').copyFolder(
                folder, creator=user, name=name, parentType=parentType,
                parent=parent, description=description, public=public,
                progress=ctx)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='folder', level=AccessType.WRITE)
    @describeRoute(
        Description('Remove all contents from a folder.')
        .notes('Cleans out all the items and subfolders from under a folder, '
               'but does not remove the folder itself.')
        .param('id', 'The ID of the folder to clean.', paramType='path')
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean', default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the folder.', 403)
    )
    def deleteContents(self, folder, params):
        progress = self.boolParam('progress', params, default=False)
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Clearing folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self.model('folder').subtreeCount(folder) - 1)
            self.model('folder').clean(folder, progress=ctx)
        return {'message': 'Cleaned folder %s.' % folder['name']}
