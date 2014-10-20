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
import json
import os

from bson.objectid import ObjectId
from .model_base import Model, ValidationException
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
            dupItem = self.findOne(q, fields=['_id'])

            q = {
                'parentId': doc['folderId'],
                'name': name,
                'parentCollection': 'folder'
            }
            dupFolder = self.model('folder').findOne(q, fields=['_id'])
            if dupItem is None and dupFolder is None:
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
            pathFromRoot = self.parentsToRoot(doc, user=user, force=True)
            baseParent = pathFromRoot[0]
            doc['baseParentId'] = baseParent['object']['_id']
            doc['baseParentType'] = baseParent['type']
            self.save(doc)
        if doc is not None and 'lowerName' not in doc:
            self.save(doc)

        return doc

    def move(self, item, folder):
        """
        Move the given item from its current folder into another folder.

        :param item: The item to move.
        :type item: dict
        :param folder: The folder to move the item into.
        :type folder: dict.
        """
        def propagateSizeChange(item, inc):
            self.model('folder').increment(query={
                '_id': item['folderId']
            }, field='size', amount=inc, multi=False)

            self.model(item['baseParentType']).increment(query={
                '_id': item['baseParentId']
            }, field='size', amount=inc, multi=False)

        propagateSizeChange(item, -item['size'])

        item['folderId'] = folder['_id']
        item['baseParentType'] = folder['baseParentType']
        item['baseParentId'] = folder['baseParentId']

        propagateSizeChange(item, item['size'])

        return self.save(item)

    def childFiles(self, item, limit=50, offset=0, sort=None, **kwargs):
        """
        Generator function that yields child files in the item.  Passes any
        kwargs to the find function.

        :param item: The parent item.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        """
        q = {
            'itemId': item['_id']
        }

        cursor = self.model('file').find(
            q, limit=limit, offset=offset, sort=sort, **kwargs)
        for file in cursor:
            yield file

    def remove(self, item, **kwargs):
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
            fileKwargs = kwargs.copy()
            fileKwargs.pop('updateItemSize', None)
            self.model('file').remove(file, updateItemSize=False, **fileKwargs)

        # Delete pending uploads into this item
        uploads = self.model('upload').find({
            'parentId': item['_id'],
            'parentType': 'item'
        }, limit=0)
        for upload in uploads:
            self.model('upload').remove(upload, **kwargs)

        # Delete the item itself
        Model.remove(self, item)

    def textSearch(self, query, user=None, filters=None, limit=50, offset=0,
                   sort=None, fields=None):
        """
        Custom override of Model.textSearch to filter items by permissions
        of the parent folder.
        """
        if not filters:
            filters = {}

        # get the non-filtered search result from Model.textSearch
        cursor = Model.textSearch(self, query=query, limit=0, sort=sort,
                                  filters=filters)

        # list where we will store the filtered results
        filtered = []

        # cache dictionary mapping folderId's to read permission
        folderCache = {}

        # loop through all results in the non-filtered list
        i = 0
        for result in cursor:
            # check if the folderId is cached
            folderId = result['folderId']

            if folderId not in folderCache:
                # if the folderId is not cached check for read permission
                # and set the cache
                folder = self.model('folder').load(folderId, force=True)
                folderCache[folderId] = self.model('folder').hasAccess(
                    folder, user=user, level=AccessType.READ)

            if folderCache[folderId] is True:
                if i < offset:
                    i += 1
                    continue

                filtered.append(result)

                # once we have hit the requested limit, return
                if len(filtered) >= limit:
                    break

        cursor.close()
        return filtered

    def hasAccess(self, item, user=None, level=AccessType.READ):
        """
        Test access for a given user to this item. Simply calls this method
        on the parent folder.
        """
        folder = self.model('folder').load(item['folderId'], force=True)
        return self.model('folder').hasAccess(folder, user=user, level=level)

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
        :param description: Description for the item.
        :type description: str
        :param folder: The parent folder of the item.
        :param creator: User document representing the creator of the group.
        :type creator: dict
        :returns: The item document that was created.
        """
        now = datetime.datetime.utcnow()

        if not type(creator) is dict or '_id' not in creator:
            # Internal error -- this shouldn't be called without a user.
            raise Exception('Creator must be a user.')

        if 'baseParentType' not in folder:
            pathFromRoot = self.parentsToRoot({'folderId': folder['_id']},
                                              creator, force=True)
            folder['baseParentType'] = pathFromRoot[0]['type']
            folder['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'name': name,
            'description': description,
            'folderId': ObjectId(folder['_id']),
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
        item['updated'] = datetime.datetime.utcnow()

        # Validate and save the item
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
            item['meta'] = {}

        # Add new metadata to existing metadata
        item['meta'].update(metadata.items())

        # Remove metadata fields that were set to null (use items in py3)
        toDelete = [k for k, v in item['meta'].iteritems() if v is None]
        for key in toDelete:
            del item['meta'][key]

        item['updated'] = datetime.datetime.utcnow()

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

    def copyItem(self, srcItem, creator, name=None, folder=None,
                 description=None):
        """
        Copy an item, including duplicating files and metadata.

        :param srcItem: the item to copy.
        :type srcItem: dict
        :param creator: the user who will own the copied item.
        :param name: The name of the new item.  None to copy the original name.
        :type name: str
        :param folder: The parent folder of the new item.  None to store in the
                same folder as the original item.
        :param description: Description for the new item.  None to copy the
                original description.
        :type description: str
        :returns: the new item.
        """
        if name is None:
            name = srcItem['name']
        if folder is None:
            folder = self.model('folder').load(srcItem['folderId'], force=True)
        if description is None:
            description = srcItem['description']
        newItem = self.createItem(
            folder=folder, name=name, creator=creator, description=description)
        # copy metadata
        self.setMetadata(newItem, srcItem.get('meta', {}))
        # copy files
        for file in self.childFiles(item=srcItem, limit=0):
            self.model('file').copyFile(file, creator=creator, item=newItem)
        return self.filter(newItem)

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True):
        """
        Generate a list of files within this item.
        :param doc: the item to list.
        :param user: a user used to validate data that is returned.  This isn't
                     used, but is present to be consistent across all model
                     implementations of fileList.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the json string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True and the item has more than one file, metadata,
                        or the sole file is not named the same as the item,
                        then the returned paths include the item name.
        """
        if subpath:
            files = [file for file in self.childFiles(item=doc, limit=2)]
            if (len(files) != 1 or files[0]['name'] != doc['name'] or
                    (includeMetadata and len(doc.get('meta', {})))):
                path = os.path.join(path, doc['name'])
        metadataFile = "girder-item-metadata.json"
        for file in self.childFiles(item=doc, limit=0, timeout=False):
            if file['name'] == metadataFile:
                metadataFile = None
            yield (os.path.join(path, file['name']),
                   self.model('file').download(file, headers=False))
        if includeMetadata and metadataFile and len(doc.get('meta', {})):
            def stream():
                yield json.dumps(doc['meta'])
            yield (os.path.join(path, metadataFile), stream)
