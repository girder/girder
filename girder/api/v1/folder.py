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
from girder.exceptions import RestException
from girder.models.folder import Folder as FolderModel
from girder.utility import ziputil
from girder.utility.progress import ProgressContext


class Folder(Resource):
    """API Endpoint for folders."""

    def __init__(self):
        super(Folder, self).__init__()
        self.resourceName = 'folder'
        self._model = FolderModel()
        self.route('DELETE', (':id',), self.deleteFolder)
        self.route('DELETE', (':id', 'contents'), self.deleteContents)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getFolder)
        self.route('GET', (':id', 'details'), self.getFolderDetails)
        self.route('GET', (':id', 'access'), self.getFolderAccess)
        self.route('GET', (':id', 'download'), self.downloadFolder)
        self.route('GET', (':id', 'rootpath'), self.rootpath)
        self.route('POST', (), self.createFolder)
        self.route('PUT', (':id',), self.updateFolder)
        self.route('PUT', (':id', 'access'), self.updateFolderAccess)
        self.route('POST', (':id', 'copy'), self.copyFolder)
        self.route('PUT', (':id', 'metadata'), self.setMetadata)
        self.route('DELETE', (':id', 'metadata'), self.deleteMetadata)

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Search for folders by certain properties.')
        .notes('You must pass either a "folderId" or "text" field'
               'to specify how you are searching for folders.  '
               'If you omit one of these parameters the request will fail and respond : '
               '"Invalid search mode."')
        .responseClass('Folder', array=True)
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', "The ID of the folder's parent.", required=False)
        .param('text', 'Pass to perform a text search.', required=False)
        .param('name', 'Pass to lookup a folder by exact name match. Must '
               'pass parentType and parentId as well when using this.', required=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Read access was denied on the parent resource.', 403)
    )
    def find(self, parentType, parentId, text, name, limit, offset, sort):
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
        user = self.getCurrentUser()

        if parentType and parentId:
            parent = self.model(parentType).load(
                parentId, user=user, level=AccessType.READ, exc=True)

            filters = {}
            if text:
                filters['$text'] = {
                    '$search': text
                }
            if name:
                filters['name'] = name

            return list(self._model.childFolders(
                parentType=parentType, parent=parent, user=user,
                offset=offset, limit=limit, sort=sort, filters=filters))
        elif text:
            return list(self._model.textSearch(
                text, user=user, limit=limit, offset=offset, sort=sort))
        else:
            raise RestException('Invalid search mode.')

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get detailed information about a folder.')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the folder.', 403)
    )
    def getFolderDetails(self, folder):
        return {
            'nItems': self._model.countItems(folder),
            'nFolders': self._model.countFolders(
                folder, user=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.cookie
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Download an entire folder as a zip archive.')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .jsonParam('mimeFilter', 'JSON list of MIME types to include.', required=False,
                   requireArray=True)
        .produces('application/zip')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the folder.', 403)
    )
    def downloadFolder(self, folder, mimeFilter):
        """
        Returns a generator function that will be used to stream out a zip
        file containing this folder's contents, filtered by permissions.
        """
        setResponseHeader('Content-Type', 'application/zip')
        setContentDisposition(folder['name'] + '.zip')
        user = self.getCurrentUser()

        def stream():
            zip = ziputil.ZipGenerator(folder['name'])
            for (path, file) in self._model.fileList(
                    folder, user=user, subpath=False, mimeFilter=mimeFilter):
                for data in zip.addFile(file, path):
                    yield data
            yield zip.footer()
        return stream

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Update a folder or move it into a new parent.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.WRITE)
        .param('name', 'Name of the folder.', required=False, strip=True)
        .param('description', 'Description for the folder.', required=False, strip=True)
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'], strip=True)
        .param('parentId', 'Parent ID for the new parent of this folder.', required=False)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='form', requireObject=True, required=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the folder or its new parent object.', 403)
    )
    def updateFolder(self, folder, name, description, parentType, parentId, metadata):
        user = self.getCurrentUser()
        if name is not None:
            folder['name'] = name
        if description is not None:
            folder['description'] = description

        folder = self._model.updateFolder(folder)
        if metadata:
            folder = self._model.setMetadata(folder, metadata)

        if parentType and parentId:
            parent = self.model(parentType).load(
                parentId, level=AccessType.WRITE, user=user, exc=True)
            if (parentType, parent['_id']) != (folder['parentCollection'], folder['parentId']):
                folder = self._model.move(folder, parent, parentType)

        return folder

    @access.user(scope=TokenScope.DATA_OWN)
    @filtermodel(model=FolderModel, addFields={'access'})
    @autoDescribeRoute(
        Description('Update the access control list for a folder.')
        .modelParam('id', model=FolderModel, level=AccessType.ADMIN)
        .jsonParam('access', 'The JSON-encoded access control list.', requireObject=True)
        .jsonParam('publicFlags', 'JSON list of public access flags.', requireArray=True,
                   required=False)
        .param('public', 'Whether the folder should be publicly visible.',
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
    def updateFolderAccess(self, folder, access, publicFlags, public, recurse, progress):
        user = self.getCurrentUser()
        progress = progress and recurse  # Only enable progress in recursive case
        with ProgressContext(progress, user=user, title='Updating permissions',
                             message='Calculating progress...') as ctx:
            if progress:
                ctx.update(total=self._model.subtreeCount(
                    folder, includeItems=False, user=user, level=AccessType.ADMIN))
            return self._model.setAccessList(
                folder, access, save=True, recurse=recurse, user=user,
                progress=ctx, setPublic=public, publicFlags=publicFlags)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Create a new folder.')
        .responseClass('Folder')
        .param('parentType', "Type of the folder's parent", required=False,
               enum=['folder', 'user', 'collection'], default='folder')
        .param('parentId', "The ID of the folder's parent.")
        .param('name', 'Name of the folder.', strip=True)
        .param('description', 'Description for the folder.', required=False,
               default='', strip=True)
        .param('reuseExisting', 'Return existing folder if it exists rather than '
               'creating a new one.', required=False,
               dataType='boolean', default=False)
        .param('public', 'Whether the folder should be publicly visible. By '
               'default, inherits the value from parent folder, or in the '
               'case of user or collection parentType, defaults to False.',
               required=False, dataType='boolean')
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='form', requireObject=True, required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent', 403)
    )
    def createFolder(self, public, parentType, parentId, name, description,
                     reuseExisting, metadata):
        user = self.getCurrentUser()
        parent = self.model(parentType).load(
            id=parentId, user=user, level=AccessType.WRITE, exc=True)

        newFolder = self._model.createFolder(
            parent=parent, name=name, parentType=parentType, creator=user,
            description=description, public=public, reuseExisting=reuseExisting)
        if metadata:
            newFolder = self._model.setMetadata(newFolder, metadata)
        return newFolder

    @access.public(scope=TokenScope.DATA_READ)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Get a folder by ID.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the folder.', 403)
    )
    def getFolder(self, folder):
        return folder

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Get the access control list for a folder.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the folder.', 403)
    )
    def getFolderAccess(self, folder):
        return self._model.getFullAccessList(folder)

    @access.user(scope=TokenScope.DATA_OWN)
    @autoDescribeRoute(
        Description('Delete a folder by ID.')
        .modelParam('id', model=FolderModel, level=AccessType.ADMIN)
        .param('progress', 'Whether to record progress on this task.',
               required=False, dataType='boolean', default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the folder.', 403)
    )
    def deleteFolder(self, folder, progress):
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Deleting folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self._model.subtreeCount(folder))
            self._model.remove(folder, progress=ctx)
        return {'message': 'Deleted folder %s.' % folder['name']}

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Set metadata fields on an folder.')
        .responseClass('Folder')
        .notes('Set metadata fields to null in order to delete them.')
        .modelParam('id', model=FolderModel, level=AccessType.WRITE)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='body', requireObject=True)
        .param('allowNull', 'Whether "null" is allowed as a metadata value.', required=False,
               dataType='boolean', default=False)
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the folder.', 403)
    )
    def setMetadata(self, folder, metadata, allowNull):
        return self._model.setMetadata(folder, metadata, allowNull=allowNull)

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=FolderModel)
    @autoDescribeRoute(
        Description('Copy a folder.')
        .responseClass('Folder')
        .modelParam('id', 'The ID of the original folder.', model=FolderModel,
                    level=AccessType.READ)
        .param('parentType', "Type of the new folder's parent", required=False,
               enum=['folder', 'user', 'collection'])
        .param('parentId', 'The ID of the parent document.', required=False)
        .param('name', 'Name for the new folder.', required=False)
        .param('description', "Description for the new folder.", required=False)
        .param('public', "Whether the folder should be publicly visible. By "
               "default, inherits the value from parent folder, or in the case "
               "of user or collection parentType, defaults to False. If "
               "'original', use the value of the original folder.",
               required=False, enum=['true', 'false', 'original'])
        .param('progress', 'Whether to record progress on this task.',
               required=False, dataType='boolean', default=False)
        .errorResponse(('A parameter was invalid.',
                        'ID was invalid.'))
        .errorResponse('Read access was denied on the original folder.\n\n'
                       'Write access was denied on the parent.', 403)
    )
    def copyFolder(self, folder, parentType, parentId, name, description, public, progress):
        user = self.getCurrentUser()
        parentType = parentType or folder['parentCollection']
        if parentId:
            parent = self.model(parentType).load(
                id=parentId, user=user, level=AccessType.WRITE, exc=True)
        else:
            parent = None

        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Copying folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self._model.subtreeCount(folder))
            return self._model.copyFolder(
                folder, creator=user, name=name, parentType=parentType,
                parent=parent, description=description, public=public, progress=ctx)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Remove all contents from a folder.')
        .notes('Cleans out all the items and subfolders from under a folder, '
               'but does not remove the folder itself.')
        .modelParam('id', 'The ID of the folder to clean.', model=FolderModel,
                    level=AccessType.WRITE)
        .param('progress', 'Whether to record progress on this task.',
               required=False, dataType='boolean', default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied on the folder.', 403)
    )
    def deleteContents(self, folder, progress):
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Clearing folder %s' % folder['name'],
                             message='Calculating folder size...') as ctx:
            # Don't do the subtree count if we weren't asked for progress
            if progress:
                ctx.update(total=self._model.subtreeCount(folder) - 1)
            self._model.clean(folder, progress=ctx)
        return {'message': 'Cleaned folder %s.' % folder['name']}

    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(FolderModel)
    @autoDescribeRoute(
        Description('Delete metadata fields on a folder.')
        .responseClass('Folder')
        .modelParam('id', model=FolderModel, level=AccessType.WRITE)
        .jsonParam(
            'fields', 'A JSON list containing the metadata fields to delete',
            paramType='body', schema={
                'type': 'array',
                'items': {
                    'type': 'string'
                }
            }
        )
        .errorResponse(('ID was invalid.',
                        'Invalid JSON passed in request body.',
                        'Metadata key name was invalid.'))
        .errorResponse('Write access was denied for the folder.', 403)
    )
    def deleteMetadata(self, folder, fields):
        return self._model.deleteMetadata(folder, fields)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get the path to the root of the folder\'s hierarchy.')
        .modelParam('id', model=FolderModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the folder.', 403)
    )
    def rootpath(self, folder, params):
        return self._model.parentsToRoot(folder, user=self.getCurrentUser())
