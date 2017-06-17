#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2017 Kitware Inc.
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


class SetupDatabaseTestCase(base.TestCase):
    def testAdmin(self):
        admin = self.model('user').findOne({'login': 'admin'})
        self.assertDictContains({
            'firstName': 'First',
            'lastName': 'Last',
            'email': 'admin@email.com',
            'admin': True
        }, admin, 'Admin user')

        folder = self.model('folder').findOne({'parentId': admin['_id']})
        self.assertDictContains({
            'name': 'folder'
        }, folder, 'imported folder')

        item = self.model('item').findOne({'folderId': folder['_id']})
        self.assertDictContains({
            'name': 'file.txt'
        }, item, 'imported item')

        file = self.model('file').findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'imported file')

    def testUserDefaultFolders(self):
        user = self.model('user').findOne({'login': 'defaultfolders'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'One',
            'admin': False
        }, user, 'defaultFolders user')

        folder = self.model('folder').findOne({'parentId': user['_id'], 'name': 'Public'})
        self.assertDictContains({
            'public': True
        }, folder, 'automatically created public folder')

        folder = self.model('folder').findOne(
            {'parentId': user['_id'], 'name': 'Additional folder'})
        self.assertDictContains({
            'public': True
        }, folder, 'manually created public folder')

    def testUserImportedFolders(self):
        user = self.model('user').findOne({'login': 'importedfolders'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'Two',
            'admin': False
        }, user, 'defaultFolders user')

        folder = self.model('folder').findOne({'parentId': user['_id']})
        self.assertDictContains({
            'name': 'folder'
        }, folder, 'imported folder')

        item = self.model('item').findOne({'folderId': folder['_id']})
        self.assertDictContains({
            'name': 'file.txt'
        }, item, 'imported item')

        file = self.model('file').findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'imported file')

    def testUserFolderWithAlternateCreator(self):
        admin = self.model('user').findOne({'login': 'admin'})
        user = self.model('user').findOne({'login': 'creatortest'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'Three',
            'admin': False
        }, user, 'creatortest user')

        folder = self.model('folder').findOne({'parentId': user['_id']})
        self.assertDictContains({
            'name': 'Created by admin',
            'creatorId': admin['_id']
        }, folder, 'admin created folder')

    def testManuallyCreatedCollection(self):
        admin = self.model('user').findOne({'login': 'admin'})
        user = self.model('user').findOne({'login': 'defaultfolders'})

        collection = self.model('collection').findOne({'name': 'Public Collection'})
        self.assertDictContains({
            'description': 'This is an example collection',
            'public': True,
            'creatorId': admin['_id']
        }, collection, 'Public collection')

        folder = self.model('folder').findOne(
            {'name': 'Folder 1', 'parentId': collection['_id']})
        self.assertDictContains({
            'description': 'This is a public folder',
            'public': True,
            'creatorId': admin['_id']
        }, folder, 'Public folder')

        item = self.model('item').findOne(
            {'name': 'Item 1', 'folderId': folder['_id']})
        self.assertDictContains({
            'description': 'This is an item',
            'creatorId': admin['_id']
        }, item, 'Item 1')

        file = self.model('file').findOne(
            {'name': 'File1.txt', 'itemId': item['_id']})
        self.assertDictContains({
            'mimeType': 'text/plain'
        }, file, 'File1.txt')

        file = self.model('file').findOne(
            {'name': 'File2.txt', 'itemId': item['_id']})
        self.assertDictContains({
            'mimeType': 'application/json'
        }, file, 'File2.txt')

        folder = self.model('folder').findOne(
            {'name': 'Private folder', 'parentId': folder['_id']})
        self.assertDictContains({
            'description': 'Private folder in a public folder',
            'public': False,
            'creatorId': user['_id']
        }, folder, 'Private folder')

    def assertImported(self, parent):
        admin = self.model('user').findOne({'login': 'admin'})

        folder = self.model('folder').findOne(
            {'name': 'folder1', 'parentId': parent['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'folder1')

        item = self.model('item').findOne(
            {'name': 'emptyfile.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'emptyfile')

        # empty files only create items, not files
        file = self.model('file').findOne(
            {'itemId': item['_id']})
        self.assertEqual(file, None)

        item = self.model('item').findOne(
            {'name': 'file.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'emptyfile')

        file = self.model('file').findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'file.txt')

        folder = self.model('folder').findOne(
            {'name': 'folder2', 'parentId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'folder2')

        item = self.model('item').findOne(
            {'name': 'icon.png', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'icon.png')

        file = self.model('file').findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'icon.png',
            'mimeType': 'image/png',
            'size': 1494
        }, file, 'icon.png')

    def testImportedCollection(self):
        admin = self.model('user').findOne({'login': 'admin'})

        collection = self.model('collection').findOne({'name': 'Imported collection'})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, collection, 'Public collection')
        self.assertImported(collection)

    def testImportedFolder(self):
        admin = self.model('user').findOne({'login': 'admin'})

        collection = self.model('collection').findOne({'name': 'Imported folder collection'})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, collection, 'Imported folder collection')

        folder = self.model('folder').findOne(
            {'name': 'Imported folder', 'parentId': collection['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'imported folder root')

        item = self.model('item').findOne(
            {'name': 'item.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'item.txt')

        self.assertImported(folder)
