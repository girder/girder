#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import girder_client
import json
import mock
import os
import shutil
import six

# Need to set the environment variable before importing girder
os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')  # noqa

from tests import base


def setUpModule():
    plugins = os.environ.get('ENABLED_PLUGINS', '')
    if plugins:
        base.enabledPlugins.extend(plugins.split())
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class PythonClientTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        def writeFile(dirName):
            filename = os.path.join(dirName, 'f')
            f = open(filename, 'w')
            f.write(filename)
            f.close()

        # make some temp dirs and files
        self.libTestDir = os.path.join(os.path.dirname(__file__),
                                       '_libTestDir')
        os.mkdir(self.libTestDir)
        writeFile(self.libTestDir)
        for subDir in range(0, 3):
            subDirName = os.path.join(self.libTestDir, 'sub'+str(subDir))
            os.mkdir(subDirName)
            writeFile(subDirName)

    def tearDown(self):
        shutil.rmtree(self.libTestDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def testRestCore(self):
        client = girder_client.GirderClient(port=os.environ['GIRDER_PORT'])

        # Register a user
        user = client.createResource('user', params={
            'firstName': 'First',
            'lastName': 'Last',
            'login': 'mylogin',
            'password': 'password',
            'email': 'email@email.com'
        })

        self.assertTrue(user['admin'])

        # Test authentication with bad args
        flag = False
        try:
            client.authenticate()
        except Exception:
            flag = True

        self.assertTrue(flag)

        # Test authentication failure
        flag = False
        try:
            client.authenticate(username=user['login'], password='wrong')
        except girder_client.AuthenticationError:
            flag = True

        self.assertTrue(flag)

        # Interactive login (successfully)
        with mock.patch('six.moves.input', return_value=user['login']),\
                mock.patch('getpass.getpass', return_value='password'):
            client.authenticate(interactive=True)

        # /user/me should now return our user info
        user = client.getResource('user/me')
        self.assertEqual(user['login'], 'mylogin')

        # Test HTTP error case
        flag = False
        try:
            client.getResource('user/badId')
        except girder_client.HttpError as e:
            self.assertEqual(e.status, 400)
            self.assertEqual(e.method, 'GET')
            resp = json.loads(e.responseText)
            self.assertEqual(resp['type'], 'validation')
            self.assertEqual(resp['field'], 'id')
            self.assertEqual(resp['message'], 'Invalid ObjectId: badId')
            flag = True

        self.assertTrue(flag)

        # Test some folder routes
        folders = client.listFolder(
            parentId=user['_id'], parentFolderType='user')
        self.assertEqual(len(folders), 2)

        privateFolder = publicFolder = None
        for folder in folders:
            if folder['name'] == 'Public':
                publicFolder = folder
            elif folder['name'] == 'Private':
                privateFolder = folder

        self.assertNotEqual(privateFolder, None)
        self.assertNotEqual(publicFolder, None)

        self.assertEqual(client.getFolder(privateFolder['_id']), privateFolder)

        acl = client.getFolderAccess(privateFolder['_id'])
        self.assertIn('users', acl)
        self.assertIn('groups', acl)

        client.setFolderAccess(privateFolder['_id'], json.dumps(acl),
                               public=False)
        self.assertEqual(acl, client.getFolderAccess(privateFolder['_id']))

        # Test recursive ACL propagation (not very robust test yet)
        client.createFolder(privateFolder['_id'], name='Subfolder')
        client.inheritAccessControlRecursive(privateFolder['_id'])

    def testUploadCallbacks(self):
        callbackUser = self.model('user').createUser(
            firstName='Callback', lastName='Last', login='callback',
            password='password', email='Callback@email.com')
        callbackPublicFolder = six.next(self.model('folder').childFolders(
            parentType='user', parent=callbackUser, user=None, limit=1))
        callback_counts = {'folder': 0, 'item': 0}
        folders = {}
        items = {}
        folders[self.libTestDir] = False
        folder_count = 1     # 1 for self.libTestDir
        item_count = 0
        for root, dirs, files in os.walk(self.libTestDir):
            for name in files:
                items[os.path.join(root, name)] = False
                item_count += 1
            for name in dirs:
                folders[os.path.join(root, name)] = False
                folder_count += 1

        def folder_callback(folder, filepath):
            self.assertIn(filepath, six.viewkeys(folders))
            folders[filepath] = True
            callback_counts['folder'] += 1

        def item_callback(item, filepath):
            self.assertIn(filepath, six.viewkeys(items))
            items[filepath] = True
            callback_counts['item'] += 1

        client = girder_client.GirderClient(port=os.environ['GIRDER_PORT'])
        client.authenticate('callback', 'password')

        client.add_folder_upload_callback(folder_callback)
        client.add_item_upload_callback(item_callback)
        client.upload(self.libTestDir, callbackPublicFolder['_id'])

        # make sure counts are the same (callbacks not called more than once)
        # and that all folders and files have callbacks called on them
        self.assertEqual(folder_count, callback_counts['folder'])
        self.assertEqual(item_count, callback_counts['item'])
        self.assertTrue(all(six.viewvalues(items)))
        self.assertTrue(all(six.viewvalues(folders)))

        # Upload again with reuse_existing on
        existingList = list(self.model('folder').childFolders(
            parentType='folder', parent=callbackPublicFolder,
            user=callbackUser, limit=0))
        client.upload(self.libTestDir, callbackPublicFolder['_id'],
                      reuse_existing=True)
        newList = list(self.model('folder').childFolders(
            parentType='folder', parent=callbackPublicFolder,
            user=callbackUser, limit=0))
        self.assertEqual(existingList, newList)
        self.assertEqual(len(newList), 1)
        self.assertEqual([f['name'] for f in self.model('folder').childFolders(
            parentType='folder', parent=newList[0],
            user=callbackUser, limit=0)], ['sub0', 'sub1', 'sub2'])

        # Test upload via a file-like object into a folder
        callbacks = []
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        size = os.path.getsize(path)

        def progressCallback(info):
            callbacks.append(info)

        with open(path) as f:
            with self.assertRaises(girder_client.IncorrectUploadLengthError):
                try:
                    client.uploadFile(
                        callbackPublicFolder['_id'], stream=f, name='test',
                        size=size + 1, parentType='folder')
                except girder_client.IncorrectUploadLengthError as exc:
                    self.assertEqual(
                        exc.upload['received'], exc.upload['size'] - 1)
                    upload = self.model('upload').load(exc.upload['_id'])
                    self.assertEqual(upload, None)
                    raise

        with open(path) as f:
            file = client.uploadFile(
                callbackPublicFolder['_id'], stream=f, name='test', size=size,
                parentType='folder', progressCallback=progressCallback)

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0]['current'], size)
        self.assertEqual(callbacks[0]['total'], size)
        self.assertEqual(file['name'], 'test')
        self.assertEqual(file['size'], size)
        self.assertEqual(file['mimeType'], 'application/octet-stream')

        items = list(
            self.model('folder').childItems(folder=callbackPublicFolder))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'test')

        files = list(self.model('item').childFiles(items[0]))
        self.assertEqual(len(files), 1)
