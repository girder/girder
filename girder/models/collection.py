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
            '_id', 'name', 'description', 'public', 'created', 'updated',
            'size'))

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

        doc['lowerName'] = doc['name'].lower()

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

    def createCollection(self, name, creator=None, description='', public=True,
                         reuseExisting=False):
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
        :param reuseExisting: If a collection with the given name already exists
            return that collection rather than creating a new one.
        :type reuseExisting: bool
        :returns: The collection document that was created.
        """
        if reuseExisting:
            existing = self.findOne({
                'name': name
            })
            if existing:
                return existing

        now = datetime.datetime.utcnow()

        collection = {
            'name': name,
            'description': description,
            'creatorId': creator['_id'] if creator else None,
            'created': now,
            'updated': now,
            'size': 0
        }

        self.setPublic(collection, public, save=False)
        if creator:
            self.setUserAccess(
                collection, user=creator, level=AccessType.ADMIN, save=False)

        return self.save(collection)

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
                 subpath=True, mimeFilter=None, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the collection's root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: the collection to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the collection's name to the path.
        :param mimeFilter: Optional list of MIME types to filter by. Set to
            None to include all files.
        :type mimeFilter: list or tuple
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        """
        if subpath:
            path = os.path.join(path, doc['name'])

        for folder in self.model('folder').childFolders(parentType='collection',
                                                        parent=doc, user=user):
            for (filepath, file) in self.model('folder').fileList(
                    folder, user, path, includeMetadata, subpath=True,
                    mimeFilter=mimeFilter, data=data):
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
                cursor=folders, user=user, level=level)
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
                cursor=cursor, user=user, level=AccessType.ADMIN)

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
        if user['admin']:
            return True

        policy = self.model('setting').get(SettingKey.COLLECTION_CREATE_POLICY)

        if policy['open'] is True:
            return True

        if user['_id'] in policy.get('users', ()):
            return True

        if set(policy.get('groups', ())) & set(user.get('groups', ())):
            return True

        return False

    def countFolders(self, collection, user=None, level=None):
        """
        Returns the number of top level folders under this collection. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param collection: The collection.
        :type collection: dict
        :param user: If performing access checks, the user to check against.
        :type user: dict or None
        :param level: The required access level, or None to return the raw
            top-level folder count.
        """
        fields = () if level is None else ('access', 'public')

        folderModel = self.model('folder')
        folders = folderModel.find({
            'parentId': collection['_id'],
            'parentCollection': 'collection'
        }, fields=fields)

        if level is None:
            return folders.count()
        else:
            return sum(1 for _ in folderModel.filterResultsByPermission(
                cursor=folders, user=user, level=level))

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this collection and its underlying
        folders and fixes the sizes as needed.

        :param doc: The collection.
        :type doc: dict
        """
        size = 0
        fixes = 0
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'collection'
        })
        for folder in folders:
            # fix folder size if needed
            _, f = self.model('folder').updateSize(folder)
            fixes += f
            # get total recursive folder size
            folder = self.model('folder').load(folder['_id'], force=True)
            size += self.model('folder').getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
