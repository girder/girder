# -*- coding: utf-8 -*-
import girder
import girder_client
import io
import json
import os
import requests
import shutil
import hashlib
import httmock
import unittest.mock

from girder import config, events
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.collection import Collection
from girder.models.upload import Upload
from girder.models.user import User
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
        super().setUp()

        def writeFile(dirName):
            filename = os.path.join(dirName, 'f')
            with open(filename, 'w') as f:
                f.write(filename)
            filename = os.path.join(dirName, 'f1')
            with open(filename, 'w') as f:
                f.write(filename)

        # make some temp dirs and files
        self.libTestDir = os.path.join(os.path.dirname(__file__), '_libTestDir')
        # unlink old temp dirs and files first
        shutil.rmtree(self.libTestDir, ignore_errors=True)

        os.mkdir(self.libTestDir)
        writeFile(self.libTestDir)
        for subDir in range(0, 3):
            subDirName = os.path.join(self.libTestDir, 'sub' + str(subDir))
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
            'email': 'email@girder.test'
        })
        self.client.authenticate(self.user['login'], self.password)
        self.publicFolder = self.getPublicFolder(self.user)

    def tearDown(self):
        shutil.rmtree(self.libTestDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def testSession(self):
        @httmock.urlmatch(path=r'.*/describe$')
        def mock(url, request):
            self.assertIn('some-header', request.headers)
            self.assertEqual(request.headers['some-header'], 'some-value')

        with httmock.HTTMock(mock):
            with self.client.session() as session:
                session.headers.update({'some-header': 'some-value'})

                self.client.get('describe')
                self.client.get('describe')

    def getPublicFolder(self, user):
        folders = list(self.client.listFolder(
            parentId=user['_id'], parentFolderType='user', name='Public'))
        self.assertEqual(len(folders), 1)

        return folders[0]

    def testAuthenticateRaisesHTTPError(self):
        # Test non "OK" responses throw HTTPError
        @httmock.urlmatch(path=r'.*/user/authentication$')
        def mock(url, request):
            return httmock.response(500, None, request=request)

        with httmock.HTTMock(mock):
            with self.assertRaises(requests.HTTPError):
                self.client.authenticate(self.user['login'], self.password)

    def testAuthenticateRaisesAuthenticationError(self):
        # Test 401/403 raise AuthenticationError
        @httmock.urlmatch(path=r'.*/user/authentication$')
        def mock(url, request):
            return httmock.response(401, None, request=request)

        with httmock.HTTMock(mock):
            with self.assertRaises(girder_client.AuthenticationError):
                self.client.authenticate(self.user['login'], self.password)

        @httmock.urlmatch(path=r'.*/user/authentication$')
        def mock(url, request):
            return httmock.response(403, None, request=request)

        with httmock.HTTMock(mock):
            with self.assertRaises(girder_client.AuthenticationError):
                self.client.authenticate(self.user['login'], self.password)

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
            self.client.authenticate(username=self.user['login'], password='wrong')
        except girder_client.AuthenticationError:
            flag = True

        self.assertTrue(flag)

        # Interactive login (successfully)
        with unittest.mock.patch('builtins.input', return_value=self.user['login']),\
                unittest.mock.patch('getpass.getpass', return_value='password'):
            self.client.authenticate(interactive=True)

        # /user/me should now return our user info
        user = self.client.getResource('user/me')
        self.assertEqual(user['login'], 'mylogin')

        # Test HTTP error case
        flag = False
        try:
            self.client.getResource('user/badId')
        except requests.HTTPError as e:
            self.assertEqual(e.response.status_code, 400)
            self.assertEqual(e.request.method, 'GET')
            resp = e.response.json()
            self.assertEqual(resp['type'], 'validation')
            self.assertEqual(resp['field'], 'id')
            self.assertEqual(resp['message'], 'Invalid ObjectId: badId')
            flag = True

        self.assertTrue(flag)

        # Test some folder routes
        folders = list(self.client.listFolder(
            parentId=user['_id'], parentFolderType='user'))
        self.assertEqual(len(folders), 2)

        privateFolder = publicFolder = None
        for folder in folders:
            if folder['name'] == 'Public':
                publicFolder = folder
            elif folder['name'] == 'Private':
                privateFolder = folder

        self.assertNotEqual(privateFolder, None)
        self.assertNotEqual(publicFolder, None)

        self.assertEqual(self.client.getFolder(privateFolder['_id']), privateFolder)

        acl = self.client.getFolderAccess(privateFolder['_id'])
        self.assertIn('users', acl)
        self.assertIn('groups', acl)

        self.client.setFolderAccess(privateFolder['_id'], json.dumps(acl), public=False)
        self.assertEqual(acl, self.client.getFolderAccess(privateFolder['_id']))

        # Ensure setFolderAccess also accepts a dict
        self.client.setFolderAccess(privateFolder['_id'], acl, public=False)
        self.assertEqual(acl, self.client.getFolderAccess(privateFolder['_id']))

        # Test recursive ACL propagation (not very robust test yet)
        self.client.createFolder(privateFolder['_id'], name='Subfolder')
        self.client.inheritAccessControlRecursive(privateFolder['_id'])

        # Test collection creation and retrieval
        c1 = self.client.createCollection('c1', public=False)
        c2 = self.client.createCollection('c2', public=True)
        collections = list(self.client.listCollection())
        self.assertEqual(len(collections), 2)
        ids = [c['_id'] for c in collections]
        self.assertIn(c1['_id'], ids)
        self.assertIn(c2['_id'], ids)
        c1 = self.client.getCollection(c1['_id'])
        c2 = self.client.getCollection(c2['_id'])
        self.assertEqual(c1['name'], 'c1')
        self.assertEqual(c2['name'], 'c2')
        self.assertFalse(c1['public'])
        self.assertTrue(c2['public'])

        # Test user creation and retrieval
        u1 = self.client.createUser(
            'user1', 'user1@girder.test', 'John', 'Doe', 'password', True)
        u2 = self.client.createUser(
            'user2', 'user2@girder.test', 'John', 'Doe', 'password')
        users = list(self.client.listUser())
        self.assertEqual(len(users), 3)
        ids = [u['_id'] for u in users]
        self.assertIn(u1['_id'], ids)
        self.assertIn(u2['_id'], ids)
        u1 = self.client.getUser(u1['_id'])
        u2 = self.client.getUser(u2['_id'])
        self.assertEqual(u1['login'], 'user1')
        self.assertEqual(u2['login'], 'user2')
        self.assertTrue(u1['admin'])
        self.assertFalse(u2['admin'])

    def testUploadCallbacks(self):
        callbackUser = User().createUser(
            firstName='Callback', lastName='Last', login='callback',
            password='password', email='Callback@girder.test')
        callbackPublicFolder = next(Folder().childFolders(
            parentType='user', parent=callbackUser, user=None, limit=1))
        callbackCounts = {'folder': 0, 'item': 0}
        folders = {}
        items = {}
        folders[self.libTestDir] = False
        folderCount = 1     # 1 for self.libTestDir
        item_count = 0
        for root, dirs, files in os.walk(self.libTestDir):
            for name in files:
                items[os.path.join(root, name)] = False
                item_count += 1
            for name in dirs:
                folders[os.path.join(root, name)] = False
                folderCount += 1

        def folderCallback(folder, filepath):
            self.assertIn(filepath, folders.keys())
            folders[filepath] = True
            callbackCounts['folder'] += 1

        def itemCallback(item, filepath):
            self.assertIn(filepath, items.keys())
            items[filepath] = True
            callbackCounts['item'] += 1

        self.client.addFolderUploadCallback(folderCallback)
        self.client.addItemUploadCallback(itemCallback)
        self.client.upload(self.libTestDir, callbackPublicFolder['_id'])

        # make sure counts are the same (callbacks not called more than once)
        # and that all folders and files have callbacks called on them
        self.assertEqual(folderCount, callbackCounts['folder'])
        self.assertEqual(item_count, callbackCounts['item'])
        self.assertTrue(all(items.values()))
        self.assertTrue(all(folders.values()))

        # Upload again with reuseExisting on
        existingList = list(Folder().childFolders(
            parentType='folder', parent=callbackPublicFolder,
            user=callbackUser, limit=0))
        self.client.upload(self.libTestDir, callbackPublicFolder['_id'],
                           reuseExisting=True)
        newList = list(Folder().childFolders(
            parentType='folder', parent=callbackPublicFolder,
            user=callbackUser, limit=0))
        self.assertEqual(existingList, newList)
        self.assertEqual(len(newList), 1)
        self.assertEqual([f['name'] for f in Folder().childFolders(
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
                    upload = Upload().load(exc.upload['_id'])
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
            Folder().childItems(folder=callbackPublicFolder))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'test')

        files = list(Item().childFiles(items[0]))
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

    def testGetServerVersion2(self):
        @httmock.urlmatch(path=r'.*/system/version')
        def mock(url, request):
            return {
                'status_code': 200,
                'content-type': 'application/json',
                'content': {'apiVersion': '2.5.0'}
            }
        with httmock.HTTMock(mock):
            self.assertEqual(self.client.getServerVersion(), ['2', '5', '0'])

    def testGetServerVersion3(self):
        @httmock.urlmatch(path=r'.*/system/version')
        def mock(url, request):
            return {
                'status_code': 200,
                'content-type': 'application/json',
                'content': {'release': '3.0.0a5.dev1'}
            }
        with httmock.HTTMock(mock):
            self.assertEqual(self.client.getServerVersion(), ['3', '0', '0a5.dev1'])

    def _testUploadMethod(self, expectedHits=0):
        # track API calls
        hits = []
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        size = os.path.getsize(path)
        original_post = self.client.post

        def mock_post(*args, **kwargs):
            if 'data' in kwargs:
                hits.append(1)
            return original_post(*args, **kwargs)

        with unittest.mock.patch.object(self.client, 'post', new=mock_post):
            with open(path) as fh:
                self.client.uploadFile(
                    self.publicFolder['_id'], fh, name='test1', size=size, parentType='folder')

        self.assertEqual(len(hits), expectedHits)

    def testUploadReference(self):
        eventList = []

        def processEvent(event):
            eventList.append(event.info)

        with events.bound('model.file.finalizeUpload.after', 'lib_test', processEvent):
            path = os.path.join(self.libTestDir, 'sub0', 'f')
            size = os.path.getsize(path)
            with open(path) as fh:
                self.client.uploadFile(
                    self.publicFolder['_id'], fh, name='test1', size=size, parentType='folder',
                    reference='test1_reference')
            self.assertEqual(len(eventList), 1)
            self.assertEqual(eventList[0]['upload']['reference'], 'test1_reference')

            self.client.uploadFileToItem(str(eventList[0]['file']['itemId']), path,
                                         reference='test2_reference')
            self.assertEqual(len(eventList), 2)
            self.assertEqual(eventList[1]['upload']['reference'], 'test2_reference')
            self.assertNotEqual(eventList[0]['file']['_id'],
                                eventList[1]['file']['_id'])

            with open(path, 'ab') as fh:
                fh.write(b'test')

            self.client.uploadFileToItem(str(eventList[0]['file']['itemId']), path,
                                         reference='test3_reference')
            self.assertEqual(len(eventList), 3)
            self.assertEqual(eventList[2]['upload']['reference'], 'test3_reference')
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
            with open(testPath, 'w') as fh:
                fh.write('test')

            file = self.client.uploadFileToItem(item['_id'], testPath)
            self.assertEqual(file['mimeType'], 'text/plain')

            # Test uploading to a folder
            self.client.uploadFileToFolder(
                str(self.publicFolder['_id']), path, reference='test4_reference')
            self.assertEqual(len(eventList), 6)
            self.assertEqual(eventList[-1]['upload']['reference'], 'test4_reference')
            self.assertNotEqual(eventList[2]['file']['_id'],
                                eventList[-1]['file']['_id'])

    def testUploadFileToFolder(self):
        filepath = os.path.join(self.libTestDir, 'sub0', 'f')

        stream_filename = 'uploaded_from_stream'
        disk_filename = 'uploaded_from_disk'

        # upload filepath as a stream and as a local file, and assert the end result is the same
        with open(filepath, 'rb') as infile:
            infile.seek(0, os.SEEK_END)
            size = infile.tell()
            infile.seek(0)

            self.client.uploadStreamToFolder(str(self.publicFolder['_id']), infile, stream_filename,
                                             size, mimeType='text/plain')

        self.client.uploadFileToFolder(str(self.publicFolder['_id']), filepath,
                                       filename=disk_filename)

        stream_item = next(self.client.listItem(str(self.publicFolder['_id']),
                                                name=stream_filename))
        disk_item = next(self.client.listItem(str(self.publicFolder['_id']),
                                              name=disk_filename))

        # assert names and sizes are correct
        self.assertEqual(stream_filename, stream_item['name'])
        self.assertEqual(size, stream_item['size'])
        self.assertEqual(disk_filename, disk_item['name'])
        self.assertEqual(size, disk_item['size'])

        # assert every other field (besides unique ones) are identical
        unique_attrs = ('_id', 'name', 'created', 'updated')
        self.assertEqual({k: v for (k, v) in stream_item.items() if k not in unique_attrs},
                         {k: v for (k, v) in disk_item.items() if k not in unique_attrs})

    def testUploadContent(self):
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        size = os.path.getsize(path)
        with open(path) as fh:
            file = self.client.uploadFile(
                self.publicFolder['_id'], fh, name='test1', size=size, parentType='folder',
                reference='test1_reference')

        contents = "you've changed!"
        size = len(contents)
        stream = io.StringIO(contents)
        self.client.uploadFileContents(file['_id'], stream, size)

        file = File().load(file['_id'], force=True)
        sha = hashlib.sha512()
        sha.update(contents.encode('utf8'))
        self.assertEqual(file['sha512'], sha.hexdigest())

    def testListFile(self):
        # Creating item
        item = self.client.createItem(self.publicFolder['_id'], 'SomethingUnique')

        # Upload 2 different files to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file1 = self.client.uploadFileToItem(item['_id'], path)

        path = os.path.join(self.libTestDir, 'sub1', 'f1')
        file2 = self.client.uploadFileToItem(item['_id'], path)

        # Test that pagination is handled for us internally
        old = girder_client.DEFAULT_PAGE_LIMIT
        girder_client.DEFAULT_PAGE_LIMIT = 1

        # Get files from item
        files = list(self.client.listFile(item['_id']))

        self.assertEqual(len(files), 2)

        self.assertEqual(file1['_id'], files[0]['_id'])
        self.assertEqual(file2['_id'], files[1]['_id'])

        girder_client.DEFAULT_PAGE_LIMIT = old

    def testDownloadInline(self):
        # Create item
        item = self.client.createItem(self.publicFolder['_id'], 'SomethingMoreUnique')
        # Upload file to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file = self.client.uploadFileToItem(item['_id'], path)

        obj = io.BytesIO()

        # Download file to object stream
        self.client.downloadFile(file['_id'], obj)
        obj.seek(0)

        # Open file at path uloaded from, compare
        # to file downloaded to stream
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), obj.read())

    def testDownloadIterator(self):
        # Create item
        item = self.client.createItem(self.publicFolder['_id'], 'SomethingMoreUnique')
        # Upload file to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file = self.client.uploadFileToItem(item['_id'], path)

        buf = io.BytesIO()

        # Download file to object stream
        for chunk in self.client.downloadFileAsIterator(file['_id'], chunkSize=10):
            buf.write(chunk)

        buf.seek(0)

        # Open file at path uloaded from, compare
        # to content of the iterator.
        with open(path, 'rb') as f:
            self.assertEqual(f.read(), buf.read())

    def testDownloadCache(self):
        item = self.client.createItem(self.publicFolder['_id'], 'SomethingEvenMoreUnique')
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file = self.client.uploadFileToItem(item['_id'], path)

        # create another client with caching enabled
        cacheSettings = {'directory': os.path.join(self.libTestDir, 'cache')}
        client = girder_client.GirderClient(
            port=os.environ['GIRDER_PORT'], cacheSettings=cacheSettings)
        client.authenticate(self.user['login'], self.password)
        self.assertNotEqual(client.cache, None)

        # track file downloads
        hits = []

        @httmock.urlmatch(path=r'.*/file/.+/download$')
        def mock(url, request):
            hits.append(url)

        expected = b'tests/cases/py_client/_libTestDir/sub0/f'

        with httmock.HTTMock(mock):
            # download the file
            obj = io.BytesIO()
            client.downloadFile(file['_id'], obj)
            self.assertTrue(obj.getvalue().endswith(expected))
            self.assertEqual(len(hits), 1)
            # this should hit the cache only
            obj = io.BytesIO()
            client.downloadFile(file['_id'], obj)
            self.assertTrue(obj.getvalue().endswith(expected))
            self.assertEqual(len(hits), 1)

        expected = b'new file contents!'
        size = len(expected)
        stream = io.BytesIO(expected)
        self.client.uploadFileContents(file['_id'], stream, size)

        with httmock.HTTMock(mock):
            # file should download again
            obj = io.BytesIO()
            client.downloadFile(file['_id'], obj)
            self.assertTrue(obj.getvalue().endswith(expected))
            self.assertEqual(len(hits), 2)

    def testDownloadFail(self):
        # Create item
        item = self.client.createItem(self.publicFolder['_id'],
                                      'SomethingMostUnique')
        # Upload file to item
        path = os.path.join(self.libTestDir, 'sub0', 'f')
        file = self.client.uploadFileToItem(item['_id'], path)

        obj = io.BytesIO()

        @httmock.urlmatch(path=r'.*/file/.+/download$')
        def mock(url, request):
            return httmock.response(500, 'error', request=request)

        # Attempt to download file to object stream, should raise HTTPError
        with httmock.HTTMock(mock):
            with self.assertRaises(requests.HTTPError):
                self.client.downloadFile(file['_id'], obj)

    def testAddMetadataToItem(self):
        item = self.client.createItem(self.publicFolder['_id'],
                                      'Itemty McItemFace', '')
        meta = {
            'nothing': 'to see here!'
        }
        self.client.addMetadataToItem(item['_id'], meta)
        updatedItem = Item().load(item['_id'], force=True)
        self.assertEqual(updatedItem['meta'], meta)

    def testAddMetadataToFolder(self):
        meta = {
            'nothing': 'to see here!'
        }
        self.client.addMetadataToFolder(self.publicFolder['_id'], meta)
        updatedFolder = Folder().load(self.publicFolder['_id'], force=True)
        self.assertEqual(updatedFolder['meta'], meta)

    def testAddMetadataToCollection(self):
        collection = self.client.createCollection('CoolCollection', description='', public=True)
        meta = {
            'nothing': 'to see here!'
        }
        self.client.addMetadataToCollection(collection['_id'], meta)
        updatedCollection = Collection().load(collection['_id'], force=True)
        self.assertEqual(updatedCollection['meta'], meta)

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
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf8')
            patchRequest['valid'] = json.loads(body) == jsonBody

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

        testPath = 'user/%s/%s/%s' % (self.user['login'],
                                      self.publicFolder['name'], itemName)
        testInvalidPath = 'user/%s/%s/%s' % (self.user['login'],
                                             self.publicFolder['name'],
                                             'RogueOne')

        # Test valid path, default
        self.assertEqual(self.client.resourceLookup(testPath)['_id'],
                         item['_id'])

        # Test invalid path, default
        with self.assertRaises(requests.HTTPError) as cm:
            self.client.resourceLookup(testInvalidPath)

        self.assertEqual(cm.exception.status, 400)
        self.assertEqual(cm.exception.method, 'GET')
        resp = json.loads(cm.exception.responseText)
        self.assertEqual(resp['type'], 'validation')
        self.assertEqual(resp['message'],
                         'Path not found: %s' % (testInvalidPath))

        # Test valid path
        self.assertEqual(
            self.client.resourceLookup(testPath)['_id'],
            item['_id'])

        # Test invalid path
        with self.assertRaises(requests.HTTPError) as cm:
            self.client.resourceLookup(testInvalidPath)

        self.assertEqual(cm.exception.response.status_code, 400)
        self.assertEqual(cm.exception.request.method, 'GET')
        resp = cm.exception.response.json()
        self.assertEqual(resp['type'], 'validation')
        self.assertEqual(resp['message'], 'Path not found: %s' % (testInvalidPath))

    def testUploadWithPath(self):
        testUser = User().createUser(
            firstName='Jeffrey', lastName='Abrams', login='jjabrams',
            password='password', email='jjabrams@girder.test')
        publicFolder = next(Folder().childFolders(
            parentType='user', parent=testUser, user=None, limit=1))
        self.client.upload(self.libTestDir, '/user/jjabrams/Public')

        parent = next(Folder().childFolders(
            parentType='folder', parent=publicFolder,
            user=testUser, limit=0))
        self.assertEqual([f['name'] for f in Folder().childFolders(
            parentType='folder', parent=parent,
            user=testUser, limit=0)], ['sub0', 'sub1', 'sub2'])

    def testUploadFileWithDifferentName(self):
        item = self.client.createItem(self.publicFolder['_id'], 'MyStash')
        path = os.path.join(self.libTestDir, 'sub1', 'f1')
        uploadedFile = self.client.uploadFileToItem(item['_id'], path, filename='g1')
        self.assertEqual(uploadedFile['name'], 'g1')

    def testGetServerVersion(self):
        # track describe API calls
        hits = []

        @httmock.urlmatch(path=r'.*/system/version$')
        def mock(url, request):
            hits.append(url)

        expected_version = girder.constants.VERSION['release']

        with httmock.HTTMock(mock):
            self.assertEqual(
                '.'.join(self.client.getServerVersion()), expected_version)
            self.assertEqual(len(hits), 1)

            self.assertEqual(
                '.'.join(self.client.getServerVersion()), expected_version)
            self.assertEqual(len(hits), 1)

            self.assertEqual(
                '.'.join(self.client.getServerVersion(useCached=False)), expected_version)
            self.assertEqual(len(hits), 2)

    def testGetServerAPIDescription(self):
        # track system/version APIi calls
        hits = []

        @httmock.urlmatch(path=r'.*/describe$')
        def mock(url, request):
            hits.append(url)

        def checkDescription(description):
            self.assertEqual(description['basePath'], '/api/v1')
            self.assertNotEqual(description['definitions'], {})
            self.assertEqual(description['info']['title'], 'Girder REST API')
            self.assertEqual(description['info']['version'], girder.constants.VERSION['release'])
            self.assertGreater(len(description['paths']), 0)

        with httmock.HTTMock(mock):
            checkDescription(self.client.getServerAPIDescription())
            self.assertEqual(len(hits), 1)

            checkDescription(self.client.getServerAPIDescription())
            self.assertEqual(len(hits), 1)

            checkDescription(self.client.getServerAPIDescription(useCached=False))
            self.assertEqual(len(hits), 2)

    def testNonJsonResponse(self):
        resp = self.client.get('user', jsonResp=False)
        self.assertIsInstance(resp.content, bytes)

    def testCreateItemWithMeta(self):
        testMeta = {
            'meta': {
                'meta': 'meta'
            }

        }
        item = self.client.createItem(self.publicFolder['_id'],
                                      'meta', metadata=json.dumps(testMeta))

        self.assertEqual(self.client.getItem(item['_id'])['meta'], testMeta)

        # Try dict form
        item = self.client.createItem(self.publicFolder['_id'],
                                      'meta-dict', metadata=testMeta)

        self.assertEqual(self.client.getItem(item['_id'])['meta'], testMeta)

    def testCreateFolderWithMeta(self):
        testMeta = {
            'meta': {
                'meta': 'meta'
            }

        }
        folder = self.client.createFolder(self.publicFolder['_id'],
                                          'meta', metadata=json.dumps(testMeta))

        self.assertEqual(self.client.getFolder(folder['_id'])['meta'], testMeta)

        # Try dict form
        folder = self.client.createFolder(self.publicFolder['_id'],
                                          'meta-dict', metadata=testMeta)

        self.assertEqual(self.client.getFolder(folder['_id'])['meta'], testMeta)
