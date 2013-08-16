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
import pymongo

from .docs import folder_docs
from ..rest import Resource, RestException
from ...models.model_base import ValidationException
from ...constants import AccessType


class Folder(Resource):

    def _filter(self, folder):
        """
        Filter a folder document for display to the user.
        """
        # TODO possibly write a folder filter with self.filterDocument
        return folder

    def find(self, params):
        """
        Get a list of folders with given search parameters. Currently accepted
        search modes are:

        1. Searching by parentId and parentType.
        2. Searching with full text search.

        To search with full text search, pass the "text" parameter. To search
        by parent, (i.e. list child folders) pass parentId and parentType,
        which must be one of ('folder' | 'community' | 'user'). You can also
        pass limit, offset, sort, and sortdir paramters.
        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        (limit, offset, sort) = self.getPagingParameters(params, 'name')

        user = self.getCurrentUser()

        if 'text' in params:
            return self.model('folder').search(
                params['text'], user=user, offset=offset, limit=limit,
                sort=sort)
        elif 'parentId' in params and 'parentType' in params:
            parentType = params['parentType'].lower()
            if parentType == 'user':
                model = self.model('user')
            elif parentType == 'community':
                pass  # TODO community
            elif parentType == 'folder':
                model = self.model('folder')
            else:
                raise RestException('The parentType must be user, community,'
                                    ' or folder.')

            parent = self.getObjectById(
                model, id=params['parentId'], user=user, checkAccess=True,
                level=AccessType.READ)
            return self.model('folder').childFolders(
                parentType=parentType, parent=parent, user=user, offset=offset,
                limit=limit, sort=sort)
        else:
            raise RestException('Invalid search mode.')

    def createFolder(self, params):
        """
        Create a new folder.
        :param parentId: The _id of the parent folder.
        :type parentId: str
        :param parentType: The type of the parent of this folder.
        :type parentType: str - 'user', 'community', or 'folder'
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

        user = self.getCurrentUser()

        if parentType not in ('folder', 'user', 'community'):
            raise RestException('Set parentType to community, folder, or user.')

        model = self.model(parentType)

        parent = self.getObjectById(model, id=params['parentId'], user=user,
                                    checkAccess=True, level=AccessType.WRITE)

        folder = self.model('folder').createFolder(
            parent=parent, name=name, parentType=parentType, creator=user,
            description=description, public=public)

        if parentType == 'user':
            folder = self.model('folder').setUserAccess(
                folder, user=user, level=AccessType.ADMIN)
        elif parentType == 'community':
            # TODO set appropriate top-level community folder permissions
            pass
        return self._filter(folder)

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            return self.find(params)
        else:  # assume it's a folder id
            user = self.getCurrentUser()
            folder = self.getObjectById(self.model('folder'), id=path[0],
                                        checkAccess=True, user=user)
            return self._filter(folder)

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to create a new folder.
        """
        return self.createFolder(params)
