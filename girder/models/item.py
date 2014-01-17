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
        self.ensureIndices(['folderId', 'lowerName'])
        self.ensureTextIndex({
            'name': 10,
            'description': 1
        })

    def validate(self, doc):
        doc['name'] = doc['name'].strip()
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
             force=False, fields=None):
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
        doc = Model.load(self, id=id, objectId=objectId, fields=fields)

        if not force and doc is not None:
            self.model('folder').load(doc['folderId'], level, user, objectId,
                                      force, fields)

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

    def search(self, query, user=None, limit=50, offset=0, sort=None):
        """
        Search for items with full text search.

        TODO
        1. Find all items that match the text search.
        2. Filter them by ensuring read access on their parent folder. As we
        fetch parent folders, keep a cache dict mapping folder ID to either
        (True | False), representing whether the user has read access to that
        folder, so we can lookup in the cache quickly without having to run to
        the database to check every time. There should be a high cache hit rate
        since items with similar text have a good chance of residing in the
        same folder, or a small set of folders.

        The current implementation is a stopgap
        """

        pass

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

        if not type(creator) is dict or not '_id' in creator:
            # Internal error -- this shouldn't be called without a user.
            raise Exception('Creator must be a user.')

        return self.save({
            'name': name,
            'description': description,
            'folderId': folder['_id'],
            'creatorId': creator['_id'],
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

    def setMetadata(self, id, user, meta):
        """
        Set metadata on an item.

        :param id: The id of the item.
        :type id: string or ObjectId
        :param user: The user requesting metadata
        :type user: dict or None
        :param meta: A dictionary containing key-value pairs to add to
                     the items meta field
        :type meta: dict
        :returns: the item document
        """
        item = self.load(id, level=AccessType.WRITE, user=user)
        if 'meta' not in item:
            item['meta'] = dict()
        item['meta'] = dict(item['meta'].items() + meta.items())  # TODO valid?
        item['updated'] = datetime.datetime.now()

        # Validate and save the item
        return self.save(item)

    def getMetadata(self, id, user, key=None):
        """
        Get the metadata on an item.

        :param id: The id of the item.
        :type id: string or ObjectId
        :param user: The user requesting metadata
        :type user: dict or None
        :param key: The specific metadata to get. If not specified, return
                    all of them
        :type key: string or tuple
        :returns: the metadata for the document
        """
        item = self.load(id, level=AccessType.READ, user=user)
        return item['meta']
