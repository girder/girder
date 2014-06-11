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

from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class FolderTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.user = self.model('user').createUser(**user)

    def testChildFolders(self):
        # Test with some bad parameters
        resp = self.request(path='/folder', method='GET', params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid search mode.')

        resp = self.request(path='/folder', method='GET', params={
            'parentType': 'invalid',
            'parentId': self.user['_id']
        })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'The parentType must be user, collection, or folder.')

        # We should only be able to see the public folder if we are anonymous
        resp = self.request(path='/folder', method='GET', params={
            'parentType': 'user',
            'parentId': self.user['_id']
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        # Test GET on the result folder
        resp = self.request(
            path='/folder/%s' % str(resp.json[0]['_id']))
        self.assertStatusOk(resp)
        self.assertEqual(type(resp.json), dict)
        self.assertFalse('access' in resp.json)

        # If we log in as the user, we should also be able to see the
        # private folder. Also test that our sortdir param works.
        resp = self.request(
            path='/folder', method='GET', user=self.user, params={
                'parentType': 'user',
                'parentId': self.user['_id'],
                'sort': 'name',
                'sortdir': -1
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['name'], 'Public')
        self.assertEqual(resp.json[1]['name'], 'Private')

    def testCreateFolder(self):
        self.ensureRequiredParams(
            path='/folder', method='POST', required=['name', 'parentId'])

        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=self.user, params={
                'parentType': 'user',
                'parentId': self.user['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        privateFolder = resp.json[0]
        publicFolder = resp.json[1]

        self.assertEqual(privateFolder['name'], 'Private')
        self.assertEqual(publicFolder['name'], 'Public')

        # Try to create a folder as anonymous; should fail
        resp = self.request(path='/folder', method='POST', params={
            'name': 'a folder',
            'parentId': publicFolder['_id']
        })
        self.assertAccessDenied(resp, AccessType.WRITE, 'folder')

        # Actually create subfolder under Public
        resp = self.request(
            path='/folder', method='POST', user=self.user, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentId'], publicFolder['_id'])
        self.assertEqual(resp.json['parentCollection'], 'folder')
        self.assertTrue(resp.json['public'])
        folder = self.model('folder').load(resp.json['_id'], force=True)
        self.assertTrue(self.model('folder').hasAccess(
            folder, self.user, AccessType.ADMIN))

        # Now fetch the children of Public, we should see it
        resp = self.request(
            path='/folder', method='GET', user=self.user, params={
                'parentType': 'folder',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'My public subfolder')

        # Try to create a folder with same name
        resp = self.request(
            path='/folder', method='POST', user=self.user, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertValidationError(resp, 'name')

    def testDeleteFolder(self):
        # Requesting with no path should fail
        resp = self.request(path='/folder', method='DELETE', user=self.user)
        self.assertStatus(resp, 400)

        # Grab one of the user's top level folders
        folders = self.model('folder').childFolders(
            parent=self.user, parentType='user', user=self.user, limit=1)
        folderResp = folders.next()

        # Add a subfolder and an item to that folder
        subfolder = self.model('folder').createFolder(
            folderResp, 'sub', parentType='folder', creator=self.user)
        item = self.model('item').createItem(
            'item', creator=self.user, folder=subfolder)

        self.assertTrue('_id' in subfolder)
        self.assertTrue('_id' in item)

        # Delete the folder
        resp = self.request(path='/folder/%s' % folderResp['_id'],
                            method='DELETE', user=self.user)
        self.assertStatusOk(resp)

        # Make sure the folder, its subfolder, and its item were all deleted
        folder = self.model('folder').load(folderResp['_id'], force=True)
        subfolder = self.model('folder').load(subfolder['_id'], force=True)
        item = self.model('item').load(item['_id'])

        self.assertEqual(folder, None)
        self.assertEqual(subfolder, None)
        self.assertEqual(item, None)

    def testLazyFieldComputation(self):
        """
        Demonstrate that a folder that is saved in the database without
        derived fields (like lowerName or baseParentId) get those values
        computed at load() time.
        """
        folder = self.model('folder').createFolder(
            parent=self.user, parentType='user', creator=self.user,
            name=' My Folder Name')

        self.assertEqual(folder['lowerName'], 'my folder name')
        self.assertEqual(folder['baseParentType'], 'user')

        # Force the item to be saved without lowerName and baseParentType fields
        del folder['lowerName']
        del folder['baseParentType']
        self.model('folder').save(folder, validate=False)

        folder = self.model('folder').find({'_id': folder['_id']}).next()
        self.assertNotHasKeys(folder, ('lowerName', 'baseParentType'))

        # Now ensure that calling load() actually populates those fields and
        # saves the results persistently
        self.model('folder').load(folder['_id'], force=True)
        folder = self.model('folder').find({'_id': folder['_id']}).next()
        self.assertHasKeys(folder, ('lowerName', 'baseParentType'))
        self.assertEqual(folder['lowerName'], 'my folder name')
        self.assertEqual(folder['baseParentType'], 'user')
        self.assertEqual(folder['baseParentId'], self.user['_id'])
