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

import cherrypy
import json
import os

from .docs import folder_docs
from ..rest import Resource, RestException, loadmodel
from ...constants import AccessType
from ...utility import ziputil


class Folder(Resource):
    """API Endpoint for folders."""

    def __init__(self):
        self.route('DELETE', (':id',), self.deleteFolder)
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getFolder)
        self.route('GET', (':id', 'access'), self.getFolderAccess)
        self.route('GET', (':id', 'download'), self.downloadFolder)
        self.route('POST', (), self.createFolder)
        self.route('PUT', (':id',), self.updateFolder)
        self.route('PUT', (':id', 'access'), self.updateFolderAccess)

    def _filter(self, folder, user):
        """
        Filter a folder document for display to the user.
        """
        keys = ['_id', 'name', 'public', 'description', 'created', 'updated',
                'size', 'parentId', 'parentCollection', 'creatorId']

        filtered = self.filterDocument(folder, allow=keys)

        filtered['_accessLevel'] = self.model('folder').getAccessLevel(
            folder, user)

        return filtered

    def find(self, params):
        """
        Get a list of folders with given search parameters. Currently accepted
        search modes are:

        1. Searching by parentId and parentType.
        2. Searching with full text search.

        To search with full text search, pass the "text" parameter. To search
        by parent, (i.e. list child folders) pass parentId and parentType,
        which must be one of ('folder' | 'collection' | 'user'). You can also
        pass limit, offset, sort, and sortdir paramters.

        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()

        if 'text' in params:
            return self.model('folder').textSearch(
                params['text'], user=user, limit=limit, project={
                    'name': 1
                })
        elif 'parentId' in params and 'parentType' in params:
            parentType = params['parentType'].lower()
            if not parentType in ('collection', 'folder', 'user'):
                raise RestException('The parentType must be user, collection,'
                                    ' or folder.')

            parent = self.model(parentType).load(
                id=params['parentId'], user=user, level=AccessType.READ,
                exc=True)

            return [self._filter(folder, user) for folder in
                    self.model('folder').childFolders(
                        parentType=parentType, parent=parent, user=user,
                        offset=offset, limit=limit, sort=sort)]
        else:
            raise RestException('Invalid search mode.')

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.READ)
    def downloadFolder(self, folder, params):
        """
        Returns a generator function that will be used to stream out a zip
        file containing this folder's contents, filtered by permissions.
        """
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="{}{}"'.format(folder['name'], '.zip')

        user = self.getCurrentUser()

        def stream():
            zip = ziputil.ZipGenerator(folder['name'])
            for data in self._downloadFolder(folder, zip, user):
                yield data

            yield zip.footer()
        return stream

    def _downloadFolder(self, folder, zip, user, path=''):
        """
        Helper method to recurse through folders and download files in them.
        """
        for sub in self.model('folder').childFolders(parentType='folder',
                                                     parent=folder, user=user,
                                                     limit=0):
            for data in self._downloadFolder(sub, zip, user, os.path.join(
                                             path, sub['name'])):
                yield data
        for item in self.model('folder').childItems(folder=folder, limit=0):
            for file in self.model('item').childFiles(item=item, limit=0):
                for data in zip.addFile(self.model('file')
                               .download(file, headers=False), os.path.join(
                                   path, file['name'])):
                    yield data

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.WRITE)
    def updateFolder(self, folder, params):
        """
        Update the folder.

        :param name: Name for the folder.
        :param description: Description for the folder.
        :param public: Public read access flag.
        :type public: bool
        """
        pass
        # TODO implement updating of a folder

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.ADMIN)
    def updateFolderAccess(self, folder, params):
        self.requireParams(['access'], params)

        public = params.get('public', 'false').lower() == 'true'
        self.model('folder').setPublic(folder, public)

        try:
            access = json.loads(params['access'])
            return self.model('folder').setAccessList(
                folder, access, save=True)
        except ValueError:
            raise RestException('The access parameter must be JSON.')

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
        self.requireParams(['name', 'parentId'], params)

        user = self.getCurrentUser()
        parentType = params.get('parentType', 'folder').lower()
        name = params['name'].strip()
        description = params.get('description', '').strip()
        public = params.get('public')

        if public is not None:
            public = public.lower() == 'true'

        if parentType not in ('folder', 'user', 'collection'):
            raise RestException('Set parentType to collection, folder, '
                                'or user.')

        model = self.model(parentType)

        parent = model.load(id=params['parentId'], user=user,
                            level=AccessType.WRITE, exc=True)

        folder = self.model('folder').createFolder(
            parent=parent, name=name, parentType=parentType, creator=user,
            description=description, public=public)

        if parentType == 'user':
            folder = self.model('folder').setUserAccess(
                folder, user=user, level=AccessType.ADMIN, save=True)
        elif parentType == 'collection':
            # TODO set appropriate top-level community folder permissions
            pass
        return self._filter(folder, user)

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.READ)
    def getFolder(self, folder, params):
        """
        Get a folder by ID.
        """
        return self._filter(folder, self.getCurrentUser())

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.ADMIN)
    def getFolderAccess(self, folder, params):
        """
        Get an access list for a folder.
        """
        return self.model('folder').getFullAccessList(folder)

    @loadmodel(map={'id': 'folder'}, model='folder', level=AccessType.ADMIN)
    def deleteFolder(self, folder, params):
        """
        Delete a folder recursively.
        """
        self.model('folder').remove(folder)
        return {'message': 'Deleted folder %s.' % folder['name']}
