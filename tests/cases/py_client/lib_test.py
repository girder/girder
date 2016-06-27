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
import time
from six import StringIO
import hashlib
import httmock

from girder import config, events
from tests import base

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


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
            filename = os.path.join(dirName, 'f1')
            f = open(filename, 'w')
            f.write(filename)
            f.close()

        # make some temp dirs and files
        self.libTestDir = os.path.join(os.path.dirname(__file__),
                                       '_libTestDir')
        # unlink old temp dirs and files first
        shutil.rmtree(self.libTestDir, ignore_errors=True)

        os.mkdir(self.libTestDir)
        writeFile(self.libTestDir)
        for subDir in range(0, 3):
            subDirName = os.path.join(self.libTestDir, 'sub'+str(subDir))
            os.mkdir(subDirName)
            writeFile(subDirName)

        self.client = girder_client.GirderClient(port=os.environ['GIRDER_PORT'])

        # Register a user
        self.password = 'password'
        self.user = self.client.createResource('user', params={
            'firstName': 'First',
            'lastName': 'Last',
            'login': 'mylogin',
            'password': self.password,
            'email': 'email@email.com'
        })
        self.client.authenticate(self.user['login'], self.password)
        self.publicFolder = self.getPublicFolder(self.user)

    def tearDown(self):
        shutil.rmtree(self.libTestDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def getPublicFolder(self, user):
            folders = self.client.listFolder(
                parentId=user['_id'], parentFolderType='user', name='Public')
            self.assertEqual(len(folders), 1)

            return folders[0]

    def testRestCore(self):
        self.assertTrue(self.user['admin'])

        # Test authentication with bad args
        flag = False
        try:
            self.client.authenticate()
        except Exception:
            flag = True

        self.assertTrue(flag)

        # Test authentication failure
        flag = False
        try:
            self.client.authenticate(username=self.user['login'],
                                     password='wrong')
        except girder_client.AuthenticationError:
            flag = True

        self.assertTrue(flag)

        # Interactive login (successfully)
        with mock.patch('six.moves.input', return_value=self.user['login']),\
                mock.patch('getpass.getpass', return_value='password'):
            self.client.authenticate(interactive=True)

        # /user/me should now return our user info
        user = self.client.getResource('user/me')
        self.assertEqual(user['login'], 'mylogin')

        # Test HTTP error case
        flag = False
        try:
            self.client.getResource('user/badId')
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
        folders = self.client.listFolder(
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

        self.assertEqual(self.client.getFolder(privateFolder['_id']),
                         privateFolder)

        acl = self.client.getFolderAccess(privateFolder['_id'])
        self.assertIn('users', acl)
        self.assertIn('groups', acl)

        self.client.setFolderAccess(privateFolder['_id'], json.dumps(acl),
                                    public=False)
        self.assertEqual(acl, self.client.getFolderAccess(privateFolder['_id']))

        # Test recursive ACL propagation (not very robust test yet)
        self.client.createFolder(privateFolder['_id'], name='Subfolder')
        self.client.inheritAccessControlRecursive(privateFolder['_id'])

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

        self.client.add_folder_upload_callback(folder_callback)
        self.client.add_item_upload_callback(item_callback)
        self.client.upload(self.libTestDir, callbackPublicFolder['_id'])

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
        self.client.upload(self.libTestDir, callbackPublicFolder['_id'],
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
                    self.client.uploadFile(
                        callbackPublicFolder['_id'], stream=f, name='test',
                        size=size + 1, parentType='folder')
                except girder_client.IncorrectUploadLengthError as exc:
                    self.assertEqual(
                        exc.upload['received'], exc.upload['size'] - 1)
                    upload = self.model('upload').load(exc.upload['_id'])
                    self.assertEqual(upload, None)
                    raise

        with open(path) as f:
            file = self.client.uploadFile(
                callbackPublicFolder['_id'], stream=f, name='test',
                size=size, parentType='folder',
                progressCallback=progressCallback)

        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0]['current'], size)
        self.assertEqual(callbacks[0]['total'], size)
        self.assertEqual(file['name'], 'test')
        self.assertEqual(file['size'], size)
        # Files with no extension should fallback to the default MIME type
        self.assertEqual(file['mimeType'], 'application/octet-stream')

        items = list(
            self.model('folder').childItems(folder=callbackPublicFolder))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'test')

        files = list(self.model('item').childFiles(items[0]))
        self.assertEqual(len(files), 1)

        # Make sure MIME type propagates correctly when explicitly passed
        with open(path) as f:
            file = self.client.uploadFile(
                callbackPublicFolder['_id'], stream=f, name='test',
                size=size, parentType='folder', mimeType='image/jpeg')
            self.assertEqual(file['mimeType'], 'image/jpeg')

        # Make sure MIME type is guessed based on file name if not passed
        with open(path) as f:
            file = self.client.uploadFile(
                callbackPublicFolder['_id'], stream=f, name='test.txt',
                size=size, parentType='folder')
            self.assertEqual(file['mimeType'], 'text/plain')

    def testUploadReference(self):
        eventList = []

        def processEvent(event):
            eventList.append(event.info)

        events.bind('data.process', 'lib_test', processEvent)

        path = os.path.join(self.libTestDir, 'sub0', 'f')
        size = os.path.getsize(path)
        self.client.uploadFile(self.publicFolder['_id'], open(path),
                               name='test1', size=size, parentType='folder',
                               reference='test1_reference')
        starttime = time.time()
        while (not events.daemon.eventQueue.empty() and
                time.time() - starttime < 5):
            time.sleep(0.05)
        self.assertEqual(len(eventList), 1)
        self.assertEqual(eventList[0]['reference'], 'test1_reference')

        self.client.uploadFileToItem(str(eventList[0]['file']['itemId']), path,
                                     reference='test2_reference')
        while (not events.daemon.eventQueue.empty() and
                time.time() - starttime < 5):
            time.sleep(0.05)
        self.assertEqual(len(eventList), 2)
        self.assertEqual(eventList[1]['reference'], 'test2_reference')
        self.assertNotEqual(eventList[0]['file']['_id'],
                            eventList[1]['file']['_id'])

        open(path, 'ab').write(b'test')
        size = os.path.getsize(path)
        self.client.uploadFileToItem(str(eventList[0]['file']['itemId']), path,
                                     reference='test3_reference')
        while (not events.daemon.eventQueue.empty() and
                time.time() - starttime < 5):
            time.sleep(0.05)
        self.assertEqual(len(eventList), 3)
        self.assertEqual(eventList[2]['reference'], 'test3_reference')
        self.assertNotEqual(eventList[0]['file']['_id'],
                            eventList[2]['file']['_id'])
        self.assertEqual(eventList[1]['file']['_id'],
                         eventList[2]['file']['_id'])

        item = self.client.createItem(self.publicFolder['_id'], 'a second item')
        # Test explicit MIME type setting
        file = self.client.uploadFileToItem(item['_id'], path,
                                            mimeType='image/jpeg')
        self.assertEqual(file['mimeType'], 'image/jpeg')

        # Test guessing of MIME type
        testPath = os.path.join(self.libTestDir, 'out.txt')
        open(testPath, 'w').write('test')
        file = self.client.uploadFileToItem(item['_id'], testPath)
        self.assertEqual(file['mimeType'], 'text/plain')

    def testUploadContent(self):
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        size = os.path.getsize(path)
        file = self.client.uploadFile(self.publicFolder['_id'], open(path),
                                      name='test1',
                                      size=size, parentType='folder',
                                      reference='test1_reference')

        contents = 'you\'ve changed!'
        size = len(contents)
        stream = StringIO(contents)
        self.client.uploadFileContents(file['_id'], stream, size)

        file = self.model('file').load(file['_id'], force=True)
        sha = hashlib.sha512()
        sha.update(contents.encode('utf8'))
        self.assertEqual(file['sha512'], sha.hexdigest())

    def testListFile(self):
        # Creating item
        item = self.client.createItem(self.publicFolder['_id'],
                                      'SomethingUnique')

        # Upload 2 different files to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file1 = self.client.uploadFileToItem(item['_id'], path)

        path = os.path.join(self.libTestDir, 'sub1', 'f1')
        file2 = self.client.uploadFileToItem(item['_id'], path)

        # Get files from item
        files = self.client.listFile(item['_id'])

        file1Id = files[0]['_id']
        file2Id = files[1]['_id']

        self.assertEqual(len(files), 2)
        self.assertEqual(file1['_id'], file1Id)
        self.assertEqual(file2['_id'], file2Id)

    def testDownloadInline(self):
        # Creating item
        item = self.client.createItem(self.publicFolder['_id'],
                                      'SomethingMoreUnique')
        # Upload file to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file = self.client.uploadFileToItem(item['_id'], path)

        obj = six.BytesIO()

        # Download file to object stream
        self.client.downloadFile(file['_id'], obj)
        obj.seek(0)

        # Open file at path uloaded from, compare
        # to file downloaded to stream
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), obj.read())

    def testAddMetadataToItem(self):
        item = self.client.createItem(self.publicFolder['_id'],
                                      'Itemty McItemFace', '')
        meta = {
            'nothing': 'to see here!'
        }
        self.client.addMetadataToItem(item['_id'], meta)
        updatedItem = self.model('item').load(item['_id'], force=True)
        self.assertEqual(updatedItem['meta'], meta)

    def testAddMetadataToFolder(self):
        meta = {
            'nothing': 'to see here!'
        }
        self.client.addMetadataToFolder(self.publicFolder['_id'], meta)
        updatedFolder = self.model('folder').load(self.publicFolder['_id'],
                                                  force=True)
        self.assertEqual(updatedFolder['meta'], meta)

    def testPatch(self):
        patchUrl = 'patch'
        patchRequest = {
            'valid': False
        }

        # Test json request
        jsonBody = {
            'foo': 'bar'
        }

        def _patchJson(url, request):
            patchRequest['valid'] = json.loads(request.body) == jsonBody

            return httmock.response(200, {}, {}, request=request)

        patch = httmock.urlmatch(
            path=r'^.*%s$' % patchUrl, method='PUT')(_patchJson)

        with httmock.HTTMock(patch):
            client = girder_client.GirderClient()
            client.put(patchUrl, json=jsonBody)

        # Check we got the right request
        self.assertTrue(patchRequest['valid'])

        # Now try raw message body
        patchRequest['valid'] = False
        rawBody = 'raw'

        def _patchRaw(url, request):
            patchRequest['valid'] = request.body == rawBody

            return httmock.response(200, {}, {}, request=request)

        patch = httmock.urlmatch(
            path=r'^.*%s$' % patchUrl, method='PUT')(_patchRaw)

        with httmock.HTTMock(patch):
            client = girder_client.GirderClient()
            client.put(patchUrl, data=rawBody)

        # Check we got the right request
        self.assertTrue(patchRequest['valid'])

    def testResourceLookup(self):
        # Creating item
        itemName = 'SomethingReallyUnique'
        item = self.client.createItem(self.publicFolder['_id'],
                                      itemName)

        testPath = "user/%s/%s/%s" % (self.user['login'],
                                      self.publicFolder['name'], itemName)
        testInvalidPath = "user/%s/%s/%s" % (self.user['login'],
                                             self.publicFolder['name'],
                                             'RogueOne')

        # Test valid path, default
        self.assertEqual(self.client.resourceLookup(testPath)['_id'],
                         item['_id'])

        # Test invalid path, default
        try:
            self.client.resourceLookup(testPath)
        except girder_client.HttpError as e:
            self.assertEqual(e.status, 400)
            self.assertEqual(e.method, 'GET')
            resp = json.loads(e.responseText)
            self.assertEqual(resp['type'], 'rest')
            self.assertEqual(resp['message'],
                             'Path not found: %s' % (testInvalidPath))

        # Test valid path, test = True
        self.assertEqual(self.client.resourceLookup(testPath,
                                                    test=True)['_id'],
                         item['_id'])

        # Test invalid path, test = True
        self.assertEqual(self.client.resourceLookup(testInvalidPath,
                                                    test=True),
                         None)

        # Test valid path, test = False
        self.assertEqual(self.client.resourceLookup(testPath,
                                                    test=False)['_id'],
                         item['_id'])

        # Test invalid path, test = False
        try:
            self.client.resourceLookup(testPath, test=False)
        except girder_client.HttpError as e:
            self.assertEqual(e.status, 400)
            self.assertEqual(e.method, 'GET')
            resp = json.loads(e.responseText)
            self.assertEqual(resp['type'], 'rest')
            self.assertEqual(resp['message'],
                             'Path not found: %s' % (testInvalidPath))
