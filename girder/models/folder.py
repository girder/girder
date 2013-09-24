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

import datetime

from .model_base import AccessControlledModel, ValidationException
from girder.constants import AccessType


class Folder(AccessControlledModel):
    """
    Folders are used to store items and can also store other folders in
    a hierarchical way, like a directory on a filesystem. Every folder has
    its own set of access control policies, but by default the access
    control list is inherited from the folder's parent folder, if it has one.
    Top-level folders are ones whose parent is a user or a collection.
    """

    def initialize(self):
        self.name = 'folder'
        self.ensureIndices(['parentId', 'name'])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException('Folder name must not be empty.', 'name')

        if not doc['parentCollection'] in ('folder', 'user', 'collection'):
            # Internal error; this shouldn't happen
            raise Exception('Invalid folder parent type: %s.' %
                            doc['parentCollection'])

        # Ensure unique name among sibling folders
        q = {
            'parentId': doc['parentId'],
            'name': doc['name'],
            'parentCollection': doc['parentCollection']
            }
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        duplicates = self.find(q, limit=1, fields=['_id'])
        if duplicates.count() != 0:
            raise ValidationException('A folder with that name already '
                                      'exists here.', 'name')

        # Ensure unique name among sibling items
        q = {
            'folderId': doc['parentId'],
            'name': doc['name']
            }
        duplicates = self.model('item').find(q, limit=1, fields=['_id'])
        if duplicates.count() != 0:
            raise ValidationException('An item with that name already '
                                      'exists here.', 'name')

        return doc

    def remove(self, folder):
        """
        Delete a folder recursively.

        :param folder: The folder document to delete.
        :type folder: dict
        """
        # Delete all child items
        items = self.model('item').find({
            'folderId': folder['_id']
        }, limit=0)
        for item in items:
            self.model('item').remove(item)

        # Delete all child folders
        folders = self.find({
            'parentId': folder['_id'],
            'parentCollection': 'folder'
        }, limit=0)
        for subfolder in folders:
            self.remove(subfolder)

        # Delete pending uploads into this folder
        uploads = self.model('upload').find({
            'parentId': folder['_id'],
            'parentType': 'folder'
        }, limit=0)
        for upload in uploads:
            self.model('upload').remove(upload)

        # Delete this folder
        AccessControlledModel.remove(self, folder)

    def childItems(self, folder, limit=50, offset=0, sort=None):
        """
        Generator function that yields child items in a folder.

        :param folder: The parent folder.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        """
        q = {
            'folderId': folder['_id']
            }

        cursor = self.model('item').find(
            q, limit=limit, offset=offset, sort=sort)
        for item in cursor:
            yield item

    def childFolders(self, parent, parentType, user=None, limit=50, offset=0,
                     sort=None):
        """
        This generator will yield child folders of a user, collection, or
        folder, with access policy filtering.

        :param parent: The parent object.
        :type parentType: Type of the parent object.
        :param parentType: The parent type.
        :type parentType: 'user', 'folder', or 'collection'
        :param user: The user running the query. Only returns folders that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        """
        parentType = parentType.lower()
        if not parentType in ('folder', 'user', 'collection'):
            raise ValidationException('The parentType must be folder, '
                                      'collection, or user.')

        q = {
            'parentId': parent['_id'],
            'parentCollection': parentType
            }

        # Perform the find; we'll do access-based filtering of the result set
        # afterward.
        cursor = self.find(q, limit=0, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=user,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def createFolder(self, parent, name, description='', parentType='folder',
                     public=None, creator=None):
        """
        Create a new folder under the given parent.

        :param parent: The parent document. Should be a folder, user, or
                       collection.
        :type parent: dict
        :param name: The name of the folder.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param parentType: What type the parent is:
                           ('folder' | 'user' | 'collection')
        :type parentType: str
        :param public: Public read access flag.
        :type public: bool or None to inherit from parent
        :param creator: User document representing the creator of this folder.
        :type creator: dict
        :returns: The folder document that was created.
        """
        assert '_id' in parent
        assert public is None or type(public) is bool

        parentType = parentType.lower()
        if not parentType in ('folder', 'user', 'collection'):
            raise ValidationException('The parentType must be folder, '
                                      'collection, or user.')

        now = datetime.datetime.now()

        if creator is None:
            creatorId = None
        else:
            creatorId = creator.get('_id', None)

        folder = {
            'name': name,
            'description': description,
            'parentCollection': parentType,
            'parentId': parent['_id'],
            'creatorId': creatorId,
            'created': now,
            'updated': now,
            'size': 0
            }

        # If this is a subfolder, default permissions are inherited from the
        # parent folder. Otherwise, the creator is granted admin access.
        if parentType == 'folder':
            self.copyAccessPolicies(src=parent, dest=folder)
        elif creator is not None:
            self.setUserAccess(folder, user=creator, level=AccessType.ADMIN)

        # Allow explicit public flag override if it's set.
        if public is not None and type(public) is bool:
            self.setPublic(folder, public=public)

        # Now validate and save the folder.
        return self.save(folder)
