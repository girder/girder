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
import os

from bson.objectid import ObjectId
from .model_base import AccessControlledModel, ValidationException
from girder.constants import AccessType, SettingKey
from girder.utility.progress import noProgress


class Collection(AccessControlledModel):
    """
    Collections are the top level roots of the data hierarchy. They are used
    to group and organize data that is meant to be shared amongst users.
    """

    def initialize(self):
        self.name = 'collection'
        self.ensureIndices(['name'])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

        self.exposeFields(level=AccessType.READ, fields=(
            'name', 'description', 'public', 'created', 'updated',
            'size'))

    def filter(self, collection, user=None):
        """Preserved override for kwarg backwards compatibility."""
        return AccessControlledModel.filter(self, doc=collection, user=user)

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        if doc['description']:
            doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException(
                'Collection name must not be empty.', 'name')

        # Ensure unique name for the collection
        q = {
            'name': doc['name']
        }
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        duplicate = self.findOne(q, fields=['_id'])
        if duplicate is not None:
            raise ValidationException('A collection with that name already '
                                      'exists.', 'name')

        return doc

    def remove(self, collection, progress=None, **kwargs):
        """
        Delete a collection recursively.

        :param collection: The collection document to delete.
        :type collection: dict
        :param progress: A progress context to record progress on.
        :type progress: girder.utility.progress.ProgressContext or None.
        """
        # Delete all folders in the community recursively
        folders = self.model('folder').find({
            'parentId': collection['_id'],
            'parentCollection': 'collection'
        })
        for folder in folders:
            self.model('folder').remove(folder, progress=progress, **kwargs)

        # Delete this collection
        AccessControlledModel.remove(self, collection)
        if progress:
            progress.update(increment=1, message='Deleted collection ' +
                            collection['name'])

    def list(self, user=None, limit=0, offset=0, sort=None):
        """
        Search for collections with full text search.
        """
        cursor = self.find({}, sort=sort)
        return self.filterResultsByPermission(
            cursor=cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)

    def createCollection(self, name, creator, description='', public=True):
        """
        Create a new collection.

        :param name: The name of the collection. Must be unique.
        :type name: str
        :param description: Description for the collection.
        :type description: str
        :param public: Public read access flag.
        :type public: bool
        :param creator: The user who is creating this collection.
        :type creator: dict
        :returns: The collection document that was created.
        """
        assert '_id' in creator

        now = datetime.datetime.utcnow()

        collection = {
            'name': name,
            'description': description,
            'creatorId': ObjectId(creator['_id']),
            'created': now,
            'updated': now,
            'size': 0
        }

        self.setPublic(collection, public=public)
        self.setUserAccess(
            collection, user=creator, level=AccessType.ADMIN)

        # Validate and save the collection
        self.save(collection)

        # Create some default folders for the collection and give the creator
        # admin access to them
        privateFolder = self.model('folder').createFolder(
            collection, 'Private', parentType='collection', public=False,
            creator=creator)
        self.model('folder').setUserAccess(
            privateFolder, creator, AccessType.ADMIN, save=True)

        if public:
            publicFolder = self.model('folder').createFolder(
                collection, 'Public', parentType='user', public=True,
                creator=creator)
            self.model('folder').setUserAccess(
                publicFolder, creator, AccessType.ADMIN, save=True)

        return collection

    def updateCollection(self, collection):
        """
        Updates a collection.

        :param collection: The collection document to update
        :type collection: dict
        :returns: The collection document that was edited.
        """
        collection['updated'] = datetime.datetime.utcnow()

        # Validate and save the collection
        return self.save(collection)

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True):
        """
        Generate a list of files within this collection's folders.

        :param doc: the collection to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the json string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the collection's name to the path.
        """
        if subpath:
            path = os.path.join(path, doc['name'])
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'collection'
        })
        for folder in folders:
            for (filepath, file) in self.model('folder').fileList(
                    folder, user, path, includeMetadata, subpath=True):
                yield (filepath, file)

    def subtreeCount(self, doc, includeItems=True, user=None, level=None):
        """
        Return the size of the folders within the collection.  The collection
        is counted as well.

        :param doc: The collection.
        :param includeItems: Whether items should be included in the count.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        count = 1
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'collection'
        }, fields=('access',))

        if level is not None:
            folders = self.filterResultsByPermission(
                cursor=folders, user=user, level=level, limit=None)
        count += sum(self.model('folder').subtreeCount(
            folder, includeItems=includeItems, user=user, level=level)
            for folder in folders)
        return count

    def setAccessList(self, doc, access, save=False, recurse=False, user=None,
                      progress=noProgress, setPublic=None):
        """
        Overrides AccessControlledModel.setAccessList to add a recursive
        option. When `recurse=True`, this will set the access list on all
        subfolders to which the given user has ADMIN access level. Any
        subfolders that the given user does not have ADMIN access on will be
        skipped.

        :param doc: The collection to set access settings on.
        :type doc: collection
        :param access: The access control list.
        :type access: dict
        :param save: Whether the changes should be saved to the database.
        :type save: bool
        :param recurse: Whether this access list should be propagated to all
            folders underneath this collection.
        :type recurse: bool
        :param user: The current user (for recursive mode filtering).
        :param progress: Progress context to update.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param setPublic: Pass this if you wish to set the public flag on the
            resources being updated.
        :type setPublic: bool or None
        """
        progress.update(increment=1, message='Updating ' + doc['name'])
        if setPublic is not None:
            self.setPublic(doc, setPublic, save=False)
        doc = AccessControlledModel.setAccessList(self, doc, access, save=save)

        if recurse:
            cursor = self.model('folder').find({
                'parentId': doc['_id'],
                'parentCollection': 'collection'
            })

            folders = self.filterResultsByPermission(
                cursor=cursor, user=user, level=AccessType.ADMIN, limit=None)

            for folder in folders:
                self.model('folder').setAccessList(
                    folder, access, save=True, recurse=True, user=user,
                    progress=progress, setPublic=setPublic)

        return doc

    def hasCreatePrivilege(self, user):
        """
        Tests whether a given user has the authority to create collections on
        this instance. This is based on the collection creation policy settings.
        By default, only admins are allowed to create collections.

        :param user: The user to test.
        :returns: bool
        """
        if user['admin'] is True:
            return True

        policy = self.model('setting').get(SettingKey.COLLECTION_CREATE_POLICY)

        if policy['open'] is True:
            return True

        if user['_id'] in policy.get('users', ()):
            return True

        if set(policy.get('groups', ())) & set(user.get('groups', ())):
            return True

        return False
