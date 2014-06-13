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

from .model_base import Model, ValidationException, AccessException
from girder.constants import AccessType


class Item(Model):
    """
    Items are leaves in the data hierarchy. They can contain 0 or more
    files within them, and can also contain arbitrary metadata.
    """

    def initialize(self):
        self.name = 'item'
        self.ensureIndices(('folderId', 'name', 'lowerName'))
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

    def filter(self, item):
        """
        Filter an item document for display to the user.
        """
        keys = ['_id', 'size', 'updated', 'description', 'created',
                'meta', 'creatorId', 'folderId', 'name', 'baseParentType',
                'baseParentId']

        filtered = self.filterDocument(item, allow=keys)

        return filtered

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
        doc['lowerName'] = doc['name'].lower()
        doc['description'] = doc['description'].strip()

        if not doc['name']:
            raise ValidationException('Item name must not be empty.', 'name')

        # Ensure unique name among sibling items and folders. If the desired
        # name collides with an existing item or folder, we will append (n)
        # onto the end of the name, incrementing n until the name is unique.
        name = doc['name']
        n = 0
        while True:
            q = {
                'name': name,
                'folderId': doc['folderId']
            }
            if '_id' in doc:
                q['_id'] = {'$ne': doc['_id']}
            dupItems = self.find(q, limit=1, fields=['_id'])

            q = {
                'parentId': doc['folderId'],
                'name': name,
                'parentCollection': 'folder'
            }
            dupFolders = self.model('folder').find(q, limit=1, fields=['_id'])
            if dupItems.count() + dupFolders.count() == 0:
                doc['name'] = name
                break
            else:
                n += 1
                name = '%s (%d)' % (doc['name'], n)

        return doc

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        """
        We override Model.load to also do permission checking.

        :param id: The id of the resource.
        :type id: string or ObjectId
        :param user: The user to check access against.
        :type user: dict or None
        :param level: The required access type for the object.
        :type level: AccessType
        :param force: If you explicity want to circumvent access
                      checking on this resource, set this to True.
        :type force: bool
        """
        doc = Model.load(self, id=id, objectId=objectId, fields=fields,
                         exc=exc)

        if not force and doc is not None:
            self.model('folder').load(doc['folderId'], level, user, objectId,
                                      force, fields)

        if doc is not None and 'baseParentType' not in doc:
            pathFromRoot = self.parentsToRoot(doc, user=user, force=force)
            baseParent = pathFromRoot[0]
            doc['baseParentId'] = baseParent['object']['_id']
            doc['baseParentType'] = baseParent['type']
            self.save(doc)
        if doc is not None and 'lowerName' not in doc:
            self.save(doc)

        return doc

    def childFiles(self, item, limit=50, offset=0, sort=None):
        """
        Generator function that yields child files in the item.

        :param item: The parent item.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        """
        q = {
            'itemId': item['_id']
        }

        cursor = self.model('file').find(
            q, limit=limit, offset=offset, sort=sort)
        for file in cursor:
            yield file

    def remove(self, item):
        """
        Delete an item, and all references to it in the database.

        :param item: The item document to delete.
        :type item: dict
        """

        # Delete all files in this item
        files = self.model('file').find({
            'itemId': item['_id']
        }, limit=0)
        for file in files:
            self.model('file').remove(file)

        # Delete pending uploads into this item
        uploads = self.model('upload').find({
            'parentId': item['_id'],
            'parentType': 'item'
        }, limit=0)
        for upload in uploads:
            self.model('upload').remove(upload)

        # Delete the item itself
        Model.remove(self, item)

    def textSearch(self, query, project, user=None, limit=20):
        """
        Custom override of Model.textSearch to filter items by permissions
        of the parent folder.
        """

        # get the non-filtered search result from Model.textSearch
        project['folderId'] = 1
        results = Model.textSearch(self, query=query, project=project)

        # list where we will store the filtered results
        filtered = []

        # cache dictionary mapping folderId's to read permission
        folderCache = {}

        # loop through all results in the non-filtered list
        for result in results:
            # check if the folderId is cached
            folderId = result['obj'].pop('folderId')

            if folderId not in folderCache:
                # if the folderId is not cached check for read permission
                # and set the cache
                folder = self.model('folder').load(folderId, force=True)
                folderCache[folderId] = self.model('folder').hasAccess(
                    folder, user=user, level=AccessType.READ)

            if folderCache[folderId] is True:
                filtered.append({
                    'name': result['obj']['name'],
                    '_id': result['obj']['_id']
                })

            # once we have hit the requested limit, return
            if len(filtered) >= limit:
                break

        return filtered

    def filterResultsByPermission(self, cursor, user, level, limit, offset,
                                  removeKeys=()):
        """
        This method is provided as a convenience for filtering a result cursor
        of items by permissions, based on the parent folder. The results in
        the cursor must contain the folderId field.
        """
        # Cache mapping folderIds -> access granted (bool)
        folderCache = {}
        count = skipped = 0
        for result in cursor:
            folderId = result['folderId']

            if folderId not in folderCache:
                folder = self.model('folder').load(folderId, force=True)
                folderCache[folderId] = self.model('folder').hasAccess(
                    folder, user=user, level=level)

            if folderCache[folderId] is True:
                if skipped < offset:
                    skipped += 1
                else:
                    yield result
                    count += 1
            if count == limit:
                    break

    def createItem(self, name, creator, folder, description=''):
        """
        Create a new item. The creator will be given admin access to it.

        :param name: The name of the item.
        :type name: str
        :param description: Description for the folder.
        :type description: str
        :param folder: The parent folder of the item.
        :param creator: User document representing the creator of the group.
        :type creator: dict
        :returns: The item document that was created.
        """
        now = datetime.datetime.now()

        if not type(creator) is dict or '_id' not in creator:
            # Internal error -- this shouldn't be called without a user.
            raise Exception('Creator must be a user.')

        if 'baseParentType' not in folder:
            pathFromRoot = self.parentsToRoot({'folderId': folder['_id']},
                                              creator)
            folder['baseParentType'] = pathFromRoot[0]['type']
            folder['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'name': name,
            'description': description,
            'folderId': folder['_id'],
            'creatorId': creator['_id'],
            'baseParentType': folder['baseParentType'],
            'baseParentId': folder['baseParentId'],
            'created': now,
            'updated': now,
            'size': 0
        })

    def updateItem(self, item):
        """
        Updates an item.

        :param item: The item document to update
        :type item: dict
        :returns: The item document that was edited.
        """
        item['updated'] = datetime.datetime.now()

        # Validate and save the collection
        return self.save(item)

    def setMetadata(self, item, metadata):
        """
        Set metadata on an item.  A rest exception is thrown in the cases where
        the metadata json object is badly formed, or if any of the metadata
        keys contains a period ('.').

        :param item: The item to set the metadata on.
        :type item: dict
        :param metadata: A dictionary containing key-value pairs to add to
                     the items meta field
        :type metadata: dict
        :returns: the item document
        """
        if 'meta' not in item:
            item['meta'] = dict()

        # Add new metadata to existing metadata
        item['meta'].update(metadata.items())

        # Remove metadata fields that were set to null (use items in py3)
        toDelete = [k for k, v in item['meta'].iteritems() if v is None]
        for key in toDelete:
            del item['meta'][key]

        item['updated'] = datetime.datetime.now()

        # Validate and save the item
        return self.save(item)

    def parentsToRoot(self, item, user=None, force=False):
        """
        Get the path to traverse to a root of the hierarchy.

        :param item: The item whose root to find
        :type item: dict
        :returns: an ordered list of dictionaries from root to the current item
        """
        curFolder = self.model('folder').load(
            item['folderId'], user=user, level=AccessType.READ, force=force)
        folderIdsToRoot = self.model('folder').parentsToRoot(
            curFolder, user=user, level=AccessType.READ, force=force)
        filteredFolder = self.model('folder').filter(curFolder, user)
        folderIdsToRoot.append({'type': 'folder', 'object': filteredFolder})
        return folderIdsToRoot
