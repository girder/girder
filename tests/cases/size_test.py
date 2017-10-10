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

from .. import base
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class SizeTestCase(base.TestCase):
    """
    Tests the correctness of sizes recorded on nodes of our data hierarchy.
    """
    def setUp(self):
        base.TestCase.setUp(self)

        # Create a user and a data hierarchy
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = User().createUser(**admin)

        coll1 = {
            'name': 'Coll1',
            'creator': self.admin
        }
        self.coll1 = Collection().createCollection(**coll1)

        coll2 = {
            'name': 'Coll2',
            'creator': self.admin
        }
        self.coll2 = Collection().createCollection(**coll2)

        folder1 = {
            'parent': self.coll1,
            'creator': self.admin,
            'parentType': 'collection',
            'name': 'Top level folder'
        }
        self.folder1 = Folder().createFolder(**folder1)

        folder2 = {
            'parent': self.folder1,
            'creator': self.admin,
            'parentType': 'folder',
            'name': 'Subfolder'
        }
        self.folder2 = Folder().createFolder(**folder2)

        item1 = {
            'name': 'Item1',
            'creator': self.admin,
            'folder': self.folder1
        }
        self.item1 = Item().createItem(**item1)

        item10 = {
            'name': 'Item10',
            'creator': self.admin,
            'folder': self.folder2
        }
        self.item10 = Item().createItem(**item10)

        file1 = {
            'creator': self.admin,
            'item': self.item1,
            'name': 'File1',
            'size': 1,
            'assetstore': self.assetstore,
            'mimeType': 'text/plain'
        }
        self.file1 = File().createFile(**file1)
        self.file1['sha512'] = ''
        File().save(self.file1, validate=False)

        file10 = {
            'creator': self.admin,
            'item': self.item10,
            'name': 'File10',
            'size': 10,
            'assetstore': self.assetstore,
            'mimeType': 'text/plain'
        }
        self.file10 = File().createFile(**file10)
        self.file10['sha512'] = ''
        File().save(self.file10, validate=False)

    def assertNodeSize(self, resource, collection, size):
        model = self.model(collection).load(resource['_id'], force=True)
        self.assertEqual(model['size'], size)

    def testMoveAndDeleteItem(self):
        self.assertNodeSize(self.item1, 'item', 1)
        self.assertNodeSize(self.item10, 'item', 10)
        self.assertNodeSize(self.folder1, 'folder', 1)
        self.assertNodeSize(self.folder2, 'folder', 10)
        self.assertNodeSize(self.coll1, 'collection', 11)

        # Move item1 down from top level folder to subfolder
        resp = self.request(
            path='/item/%s' % self.item1['_id'], method='PUT',
            user=self.admin, params={
                'folderId': self.folder2['_id']
            })
        self.assertStatusOk(resp)

        self.assertNodeSize(self.item1, 'item', 1)
        self.assertNodeSize(self.item10, 'item', 10)
        self.assertNodeSize(self.folder1, 'folder', 0)
        self.assertNodeSize(self.folder2, 'folder', 11)
        self.assertNodeSize(self.coll1, 'collection', 11)

        # Delete item1
        resp = self.request(
            path='/item/%s' % self.item1['_id'], method='DELETE',
            user=self.admin)
        self.assertStatusOk(resp)

        self.assertNodeSize(self.folder1, 'folder', 0)
        self.assertNodeSize(self.folder2, 'folder', 10)
        self.assertNodeSize(self.coll1, 'collection', 10)

    def testMoveAndDeleteFolder(self):
        # Ensure we cannot move a folder under itself
        resp = self.request(
            path='/folder/%s' % self.folder1['_id'], method='PUT',
            user=self.admin, params={
                'parentId': self.folder2['_id'],
                'parentType': 'folder'
            })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'You may not move a folder underneath itself.')

        self.assertNodeSize(self.coll1, 'collection', 11)
        self.assertNodeSize(self.coll2, 'collection', 0)

        # Move top level folder from coll1 to coll2
        resp = self.request(
            path='/folder/%s' % self.folder1['_id'], method='PUT',
            user=self.admin, params={
                'parentId': self.coll2['_id'],
                'parentType': 'collection'
            })
        self.assertStatusOk(resp)

        self.assertNodeSize(self.coll1, 'collection', 0)
        self.assertNodeSize(self.coll2, 'collection', 11)

        # Move subfolder as top level folder under admin user
        resp = self.request(
            path='/folder/%s' % self.folder2['_id'], method='PUT',
            user=self.admin, params={
                'parentId': self.admin['_id'],
                'parentType': 'user'
            })
        self.assertStatusOk(resp)
        self.assertNodeSize(self.admin, 'user', 10)
        self.assertNodeSize(self.coll2, 'collection', 1)

        # Delete the sub folder
        resp = self.request(
            path='/folder/%s' % self.folder2['_id'], method='DELETE',
            user=self.admin)
        self.assertStatusOk(resp)
        self.assertNodeSize(self.admin, 'user', 0)
        self.assertNodeSize(self.coll2, 'collection', 1)
