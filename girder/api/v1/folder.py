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
import pymongo

from .docs import folder_docs
from ..rest import Resource, RestException
from ...constants import AccessType
from ...utility import ziputil


class Folder(Resource):
    """API Endpoint for folders."""

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

    def find(self, user, params):
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

        if 'text' in params:
            return [self._filter(folder, user) for folder in
                    self.model('folder').search(
                        params['text'], user=user, offset=offset, limit=limit,
                        sort=sort)]
        elif 'parentId' in params and 'parentType' in params:
            parentType = params['parentType'].lower()
            if not parentType in ('collection', 'folder', 'user'):
                raise RestException('The parentType must be user, collection,'
                                    ' or folder.')

            parent = self.getObjectById(
                self.model(parentType), id=params['parentId'], user=user,
                checkAccess=True, level=AccessType.READ)

            return [self._filter(folder, user) for folder in
                    self.model('folder').childFolders(
                        parentType=parentType, parent=parent, user=user,
                        offset=offset, limit=limit, sort=sort)]
        else:
            raise RestException('Invalid search mode.')

    def download(self, folder, user):
        """
        Returns a generator function that will be used to stream out a zip
        file containing this folder's contents, filtered by permissions.
        """
        cherrypy.response.headers['Content-Type'] = 'application/zip'
        cherrypy.response.headers['Content-Disposition'] = \
            'attachment; filename="{}{}"'.format(folder['name'], '.zip')

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

    def updateFolder(self, folder, user, params):
        """
        Update the folder.

        :param name: Name for the folder.
        :param description: Description for the folder.
        :param public: Public read access flag.
        :type public: bool
        """
        self.model('folder').requireAccess(folder, user, AccessType.WRITE)
        # TODO implement updating of a folder

    def createFolder(self, user, params):
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

        parent = self.getObjectById(model, id=params['parentId'], user=user,
                                    checkAccess=True, level=AccessType.WRITE)

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

    @Resource.endpoint
    def DELETE(self, path, params):
        """
        Delete a folder recursively.
        """
        if not path:
            raise RestException(
                'Path parameter should be the folder ID to delete.')

        user = self.getCurrentUser()
        folder = self.getObjectById(
            self.model('folder'), id=path[0], user=user, checkAccess=True,
            level=AccessType.ADMIN)

        self.model('folder').remove(folder)
        return {'message': 'Deleted folder %s.' % folder['name']}

    @Resource.endpoint
    def GET(self, path, params):
        user = self.getCurrentUser()
        if not path:
            return self.find(user, params)
        elif len(path) == 1:  # Just get a folder by ID
            folder = self.getObjectById(self.model('folder'), id=path[0],
                                        checkAccess=True, user=user)
            return self._filter(folder, user)
        elif path[1] == 'access':
            folder = self.getObjectById(
                self.model('folder'), id=path[0], checkAccess=True, user=user,
                level=AccessType.ADMIN)
            return self.model('folder').getFullAccessList(folder)
        elif path[1] == 'download':
            folder = self.getObjectById(
                self.model('folder'), id=path[0], checkAccess=True, user=user)
            return self.download(folder, user)
        else:
            raise RestException('Unsupported operation.')

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to create a new folder.
        """
        user = self.getCurrentUser()
        return self.createFolder(user, params)

    @Resource.endpoint
    def PUT(self, path, params):
        """
        Use this endpoint to update an existing folder.
        """
        if not path:
            raise RestException('Must have a path parameter.')

        user = self.getCurrentUser()
        folder = self.getObjectById(self.model('folder'), id=path[0], user=user,
                                    checkAccess=True)

        if len(path) == 1:
            return self.updateFolder(folder, user, params)
        elif path[1] == 'access':
            self.requireParams(['access'], params)
            self.model('folder').requireAccess(folder, user, AccessType.ADMIN)

            public = params.get('public', 'false').lower() == 'true'
            self.model('folder').setPublic(folder, public)

            try:
                access = json.loads(params['access'])
                return self.model('folder').setAccessList(
                    folder, access, save=True)
            except ValueError:
                raise RestException('The access parameter must be JSON.')
