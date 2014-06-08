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

    def filter(self, collection, user=None):
        """Helper to filter the collection model."""
        filtered = self.filterDocument(
            collection, allow=('_id', 'name', 'description', 'public',
                               'created', 'updated', 'size'))

        if user:
            filtered['_accessLevel'] = self.getAccessLevel(collection, user)

        return filtered

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
        duplicates = self.find(q, limit=1, fields=['_id'])
        if duplicates.count() != 0:
            raise ValidationException('A collection with that name already'
                                      'exists.', 'name')

        return doc

    def remove(self, collection):
        """
        Delete a collection recursively.

        :param collection: The collection document to delete.
        :type collection: dict
        """
        # Delete all folders in the community recursively
        folders = self.model('folder').find({
            'parentId': collection['_id'],
            'parentCollection': 'collection'
            }, limit=0)
        for folder in folders:
            self.model('folder').remove(folder)

        # Delete this collection
        AccessControlledModel.remove(self, collection)

    def list(self, user=None, limit=50, offset=0, sort=None):
        """
        Search for collections with full text search.
        """
        cursor = self.find({}, limit=0, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=user,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

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

        now = datetime.datetime.now()

        collection = {
            'name': name,
            'description': description,
            'creatorId': creator['_id'],
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
        collection['updated'] = datetime.datetime.now()

        # Validate and save the collection
        return self.save(collection)
