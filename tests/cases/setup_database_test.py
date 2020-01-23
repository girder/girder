# -*- coding: utf-8 -*-
from .. import base
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User


class SetupDatabaseTestCase(base.TestCase):
    def testAdmin(self):
        admin = User().findOne({'login': 'admin'})
        self.assertDictContains({
            'firstName': 'First',
            'lastName': 'Last',
            'email': 'admin@girder.test',
            'admin': True
        }, admin, 'Admin user')

        folder = Folder().findOne({'parentId': admin['_id']})
        self.assertDictContains({
            'name': 'folder'
        }, folder, 'imported folder')

        item = Item().findOne({'folderId': folder['_id']})
        self.assertDictContains({
            'name': 'file.txt'
        }, item, 'imported item')

        file = File().findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'imported file')

    def testUserDefaultFolders(self):
        user = User().findOne({'login': 'defaultfolders'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'One',
            'admin': False
        }, user, 'defaultFolders user')

        folder = Folder().findOne({'parentId': user['_id'], 'name': 'Public'})
        self.assertDictContains({
            'public': True
        }, folder, 'automatically created public folder')

        folder = Folder().findOne({'parentId': user['_id'], 'name': 'Additional folder'})
        self.assertDictContains({
            'public': True
        }, folder, 'manually created public folder')
        self.assertDictContains({
            'creatorId': user['_id']
        }, folder, 'folder is created by expected user')

    def testUserImportedFolders(self):
        user = User().findOne({'login': 'importedfolders'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'Two',
            'admin': False
        }, user, 'defaultFolders user')

        folder = Folder().findOne({'parentId': user['_id']})
        self.assertDictContains({
            'name': 'folder'
        }, folder, 'imported folder')

        item = Item().findOne({'folderId': folder['_id']})
        self.assertDictContains({
            'name': 'file.txt'
        }, item, 'imported item')

        file = File().findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'imported file')

    def testUserFolderWithAlternateCreator(self):
        admin = User().findOne({'login': 'admin'})
        user = User().findOne({'login': 'creatortest'})
        self.assertDictContains({
            'firstName': 'User',
            'lastName': 'Three',
            'admin': False
        }, user, 'creatortest user')

        folder = Folder().findOne({'parentId': user['_id']})
        self.assertDictContains({
            'name': 'Created by admin',
            'creatorId': admin['_id']
        }, folder, 'admin created folder')

    def testManuallyCreatedCollection(self):
        admin = User().findOne({'login': 'admin'})
        user = User().findOne({'login': 'defaultfolders'})

        collection = Collection().findOne({'name': 'Public Collection'})
        self.assertDictContains({
            'description': 'This is an example collection',
            'public': True,
            'creatorId': admin['_id']
        }, collection, 'Public collection')

        folder = Folder().findOne({'name': 'Folder 1', 'parentId': collection['_id']})
        self.assertDictContains({
            'description': 'This is a public folder',
            'public': True,
            'creatorId': admin['_id']
        }, folder, 'Public folder')

        item = Item().findOne(
            {'name': 'Item 1', 'folderId': folder['_id']})
        self.assertDictContains({
            'description': 'This is an item',
            'creatorId': admin['_id']
        }, item, 'Item 1')

        file = File().findOne({'name': 'File1.txt', 'itemId': item['_id']})
        self.assertDictContains({
            'mimeType': 'text/plain'
        }, file, 'File1.txt')

        file = File().findOne({'name': 'File2.txt', 'itemId': item['_id']})
        self.assertDictContains({
            'mimeType': 'application/json'
        }, file, 'File2.txt')

        folder = Folder().findOne({'name': 'Private folder', 'parentId': folder['_id']})
        self.assertDictContains({
            'description': 'Private folder in a public folder',
            'public': False,
            'creatorId': user['_id']
        }, folder, 'Private folder')

    def assertImported(self, parent):
        admin = User().findOne({'login': 'admin'})

        folder = Folder().findOne({'name': 'folder1', 'parentId': parent['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'folder1')

        item = Item().findOne(
            {'name': 'emptyfile.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'emptyfile')

        file = File().findOne({'itemId': item['_id']})
        self.assertEqual(file['name'], 'emptyfile.txt')

        item = Item().findOne(
            {'name': 'file.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'emptyfile')

        file = File().findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'file.txt',
            'mimeType': 'text/plain',
            'size': 5
        }, file, 'file.txt')

        folder = Folder().findOne({'name': 'folder2', 'parentId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'folder2')

        item = Item().findOne({'name': 'icon.png', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'icon.png')

        file = File().findOne({'itemId': item['_id']})
        self.assertDictContains({
            'name': 'icon.png',
            'mimeType': 'image/png',
            'size': 1494
        }, file, 'icon.png')

    def testImportedCollection(self):
        admin = User().findOne({'login': 'admin'})

        collection = Collection().findOne({'name': 'Imported collection'})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, collection, 'Public collection')
        self.assertImported(collection)

    def testImportedFolder(self):
        admin = User().findOne({'login': 'admin'})

        collection = Collection().findOne({'name': 'Imported folder collection'})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, collection, 'Imported folder collection')

        folder = Folder().findOne({'name': 'Imported folder', 'parentId': collection['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, folder, 'imported folder root')

        item = Item().findOne({'name': 'item.txt', 'folderId': folder['_id']})
        self.assertDictContains({
            'creatorId': admin['_id']
        }, item, 'item.txt')

        self.assertImported(folder)

    def testYAMLAliases(self):
        folderModel = Folder()
        aliasedFolders = list(folderModel.find({'name': 'Common'}, force=True))
        self.assertTrue(len(aliasedFolders) == 2)

        for folder in aliasedFolders:
            self.assertTrue(
                len(list(folderModel.childItems(folder, force=True))) == 2
            )
