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

import io
import json
import mock
import moto
import os
import shutil
import zipfile

from hashlib import sha512
from .. import base, mock_s3

from girder import events
from girder.constants import SettingKey
from girder.models import getDbConnection
from girder.models.model_base import AccessException
from girder.utility.s3_assetstore_adapter import (makeBotoConnectParams,
                                                  S3AssetstoreAdapter)
from six.moves import urllib


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()

chunk1, chunk2 = ('hello ', 'world')
chunkData = chunk1.encode('utf8') + chunk2.encode('utf8')


class FileTestCase(base.TestCase):
    """
    Tests the uploading, downloading, and storage of files in each different
    type of assetstore.
    """
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
        folders = self.model('folder').childFolders(
            parent=self.user, parentType='user', user=self.user)
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder
        secondUser = {
            'email': 'second@email.com',
            'login': 'secondlogin',
            'firstName': 'Second',
            'lastName': 'User',
            'password': 'secondpassword'
        }
        self.secondUser = self.model('user').createUser(**secondUser)

        self.testForFinalizeUpload = False
        self.finalizeUploadBeforeCalled = False
        self.finalizeUploadAfterCalled = False
        events.bind('model.file.finalizeUpload.before',
                    '_testFinalizeUploadBefore', self._testFinalizeUploadBefore)
        events.bind('model.file.finalizeUpload.after',
                    '_testFinalizeUploadAfter', self._testFinalizeUploadAfter)

    def _testEmptyUpload(self, name):
        """
        Uploads an empty file to the server.
        """
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': name,
                'size': 0
            })
        self.assertStatusOk(resp)

        file = resp.json

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['size'], 0)
        self.assertEqual(file['name'], name)
        self.assertEqual(file['assetstoreId'], str(self.assetstore['_id']))

        return self.model('file').load(file['_id'], force=True)

    def _testFinalizeUploadBefore(self, event):
        self.finalizeUploadBeforeCalled = True
        self._testFinalizeUpload(event)

    def _testFinalizeUploadAfter(self, event):
        self.finalizeUploadAfterCalled = True
        self._testFinalizeUpload(event)

    def _testFinalizeUpload(self, event):
        self.assertIn('file', event.info)
        self.assertIn('upload', event.info)

        file = event.info['file']
        upload = event.info['upload']
        self.assertEqual(file['name'], upload['name'])
        self.assertEqual(file['creatorId'], upload['userId'])
        self.assertEqual(file['size'], upload['size'])

    def _testUploadFile(self, name):
        """
        Uploads a non-empty file to the server.
        """
        self.testForFinalizeUpload = True

        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': name,
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Uploading with no user should fail
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'helloWorld.txt', chunk1)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files)
        self.assertStatus(resp, 401)

        # Uploading with the wrong user should fail
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'helloWorld.txt', chunk1)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.secondUser, fields=fields,
            files=files)
        self.assertStatus(resp, 403)

        # Sending the first chunk should fail because the default minimum chunk
        # size is larger than our chunk.
        self.model('setting').unset(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE)
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'helloWorld.txt', chunk1)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Chunk is smaller than the minimum size.'
        })

        # Send the first chunk
        self.model('setting').set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 0)
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Attempting to send second chunk with incorrect offset should fail
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', name, chunk2)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)

        self.assertStatus(resp, 400)

        # Ask for completion before sending second chunk should fail
        resp = self.request(path='/file/completion', method='POST',
                            user=self.user, params={'uploadId': uploadId})
        self.assertStatus(resp, 400)

        # Request offset from server (simulate a resume event)
        resp = self.request(path='/file/offset', method='GET', user=self.user,
                            params={'uploadId': uploadId})
        self.assertStatusOk(resp)

        # Trying to send too many bytes should fail
        currentOffset = resp.json['offset']
        fields = [('offset', resp.json['offset']), ('uploadId', uploadId)]
        files = [('chunk', name, "extra_"+chunk2+"_bytes")]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Received too many bytes.'
        })

        # The offset should not have changed
        resp = self.request(path='/file/offset', method='GET', user=self.user,
                            params={'uploadId': uploadId})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], currentOffset)

        files = [('chunk', name, chunk2)]

        # Now upload the second chunk
        fields = [('offset', resp.json['offset']), ('uploadId', uploadId)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        file = resp.json

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], str(self.assetstore['_id']))
        self.assertEqual(file['name'], name)
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        return file

    def _testDownloadFile(self, file, contents):
        """
        Downloads the previously uploaded file from the server.
        :param file: The file object to download.
        :type file: dict
        :param contents: The expected contents.
        :type contents: str
        """
        resp = self.request(path='/file/%s/download' % str(file['_id']),
                            method='GET', user=self.user, isJson=False)
        self.assertStatusOk(resp)
        if contents:
            self.assertEqual(resp.headers['Content-Type'],
                             'text/plain;charset=utf-8')
            self.assertEqual(resp.headers['Content-Disposition'],
                             'attachment; filename="%s"' % file['name'])

        self.assertEqual(contents, self.getBody(resp))

        # Test downloading the file with contentDisposition=inline.
        params = {'contentDisposition': 'inline'}
        resp = self.request(path='/file/%s/download' % str(file['_id']),
                            method='GET', user=self.user, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        if contents:
            self.assertEqual(resp.headers['Content-Type'],
                             'text/plain;charset=utf-8')
            self.assertEqual(resp.headers['Content-Disposition'],
                             'inline; filename="%s"' % file['name'])

        self.assertEqual(contents, self.getBody(resp))

        # Test downloading with an offset
        resp = self.request(path='/file/%s/download' % str(file['_id']),
                            method='GET', user=self.user, isJson=False,
                            params={'offset': 1})
        if file['size']:
            self.assertStatus(resp, 206)
        else:
            self.assertStatusOk(resp)
        self.assertEqual(contents[1:], self.getBody(resp))

        # Test downloading with a range header and query range params
        respHeader = self.request(path='/file/%s/download' % str(file['_id']),
                                  method='GET', user=self.user, isJson=False,
                                  additionalHeaders=[('Range', 'bytes=2-7')])
        respQuery = self.request(path='/file/%s/download' % str(file['_id']),
                                 method='GET', user=self.user, isJson=False,
                                 params={'offset': 2, 'endByte': 8})
        for resp in [respHeader, respQuery]:
            self.assertEqual(contents[2:8], self.getBody(resp))
            self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
            length = len(contents)
            begin, end = min(length, 2), min(length, 8)
            self.assertEqual(resp.headers['Content-Length'], end - begin)
            if length:
                self.assertStatus(resp, 206)
                self.assertEqual(resp.headers['Content-Range'],
                                 'bytes %d-%d/%d' % (begin, end - 1, length))
            else:
                self.assertStatusOk(resp)

        # Test downloading with a name
        resp = self.request(
            path='/file/%s/download/%s' % (
                str(file['_id']),
                urllib.parse.quote(file['name']).encode('utf8')
            ), method='GET', user=self.user, isJson=False)
        self.assertStatusOk(resp)
        if contents:
            self.assertEqual(resp.headers['Content-Type'],
                             'text/plain;charset=utf-8')
        self.assertEqual(contents, self.getBody(resp))

    def _testDownloadFolder(self):
        """
        Test downloading an entire folder as a zip file.
        """
        # Create a subfolder
        resp = self.request(
            path='/folder', method='POST', user=self.user, params={
                'name': 'Test',
                'parentId': self.privateFolder['_id']
            })
        test = resp.json
        contents = os.urandom(1024 * 1024)  # Generate random file contents

        # Upload the file into that subfolder
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': test['_id'],
                'name': 'random.bin',
                'size': len(contents)
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the file contents
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'random.bin', contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # List files in the folder
        testFolder = self.model('folder').load(test['_id'], force=True)
        fileList = [(path, file['name'])
                    for (path, file) in self.model('folder').fileList(
                        testFolder, user=self.user,
                        subpath=True, stream=False)]
        self.assertEqual(fileList, [(u'Test/random.bin', u'random.bin')])

        # Download the folder
        resp = self.request(
            path='/folder/%s/download' % str(self.privateFolder['_id']),
            method='GET', user=self.user, isJson=False)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)

        extracted = zip.read('Private/Test/random.bin')
        self.assertEqual(extracted, contents)

        # Upload a known MIME-type file into the folder
        contents = b'not a jpeg'
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': str(self.privateFolder['_id']),
                'name': 'fake.jpeg',
                'size': len(contents),
                'mimeType': 'image/jpeg'
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the file contents
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'fake.jpeg', contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Download the folder with a MIME type filter
        resp = self.request(
            path='/folder/%s/download' % str(self.privateFolder['_id']),
            method='GET', user=self.user, isJson=False, params={
                'mimeFilter': json.dumps(['image/png', 'image/jpeg'])
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        self.assertEqual(resp.headers['Content-Disposition'],
                         'attachment; filename="Private.zip"')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)

        path = 'Private/fake.jpeg'
        self.assertEqual(zip.namelist(), [path])
        extracted = zip.read(path)
        self.assertEqual(extracted, contents)

    def _testDownloadCollection(self):
        """
        Test downloading an entire collection as a zip file.
        """
        # Create a collection
        resp = self.request(
            path='/collection', method='POST', user=self.user, params={
                'name': 'Test Collection'
            })
        self.assertStatusOk(resp)
        collection = resp.json

        # Create a folder in the collection
        resp = self.request(
            path='/folder', method='POST', user=self.user, params={
                'name': 'Test Folder',
                'parentId': collection['_id'],
                'parentType': 'collection'
            })
        self.assertStatusOk(resp)

        test = resp.json
        contents = os.urandom(64)  # Generate random file contents

        # Upload the file into that subfolder
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': test['_id'],
                'name': 'random.bin',
                'size': len(contents)
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the file contents
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'random.bin', contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Download the collection
        path = '/collection/%s/download' % str(collection['_id'])
        resp = self.request(
            path=path,
            method='GET', user=self.user, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Disposition'],
                         'attachment; filename="Test Collection.zip"')
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)

        extracted = zip.read('Test Collection/Test Folder/random.bin')
        self.assertEqual(extracted, contents)

        # Make collection public
        collection = self.model('collection').load(collection['_id'],
                                                   force=True)
        collection['public'] = True
        collection = self.model('collection').save(collection)

        # Download the collection as anonymous
        path = '/collection/%s/download' % str(collection['_id'])
        resp = self.request(
            path=path,
            method='GET', user=None, isJson=False)
        self.assertStatusOk(resp)
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        # Zip file should have no entries
        self.assertFalse(zip.namelist())

        # Upload a known MIME-type file into the collection
        contents = b'not a jpeg'
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': test['_id'],
                'name': 'fake.jpeg',
                'size': len(contents),
                'mimeType': 'image/jpeg'
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the file contents
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'fake.jpeg', contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Download the collection using a MIME type filter
        path = '/collection/%s/download' % str(collection['_id'])
        resp = self.request(
            path=path, method='GET', user=self.user, isJson=False, params={
                'mimeFilter': json.dumps(['image/png', 'image/jpeg'])
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Disposition'],
                         'attachment; filename="Test Collection.zip"')
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)

        # Only the jpeg should exist in the zip
        path = 'Test Collection/Test Folder/fake.jpeg'
        self.assertEqual(zip.namelist(), [path])
        extracted = zip.read(path)
        self.assertEqual(extracted, contents)

    def _testDeleteFile(self, file):
        """
        Deletes the previously uploaded file from the server.
        """
        resp = self.request(
            path='/file/%s' % str(file['_id']), method='DELETE', user=self.user)
        self.assertStatusOk(resp)

    def _downloadFile(self, file):
        resp = self.request(path='/file/%s/download' % str(file['_id']),
                            method='GET', user=self.user, isJson=False)
        self.assertStatusOk(resp)

        return self.getBody(resp)

    def _assertFileContent(self, file, copy):

        # Assert that the two files have the same content
        fileContent = self._downloadFile(file)
        fileCopyContent = self._downloadFile(copy)
        self.assertEqual(fileContent, fileCopyContent)

    def _testCopyFile(self, file, assertContent=True):
        # First create a test item
        params = {
            'name': 'copyItem',
            'description': 'Another item',
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertStatusOk(resp)
        item = resp.json

        # Now do the copy
        params = {
            'itemId': item['_id']
        }
        resp = self.request(path='/file/%s/copy' % str(file['_id']),
                            method='POST',  params=params, user=self.user)
        self.assertStatusOk(resp)
        copy = resp.json
        # Assert the copy is attached to the item
        self.assertEqual(copy['itemId'], item['_id'])
        # Assert the we have two different id
        self.assertNotEqual(file['_id'], copy['_id'])
        if assertContent:
            self._assertFileContent(file, copy)

    def testFilesystemAssetstore(self):
        """
        Test usage of the Filesystem assetstore type.
        """
        self.assetstore = self.model('assetstore').getCurrent()
        root = self.assetstore['root']

        # Clean out the test assetstore on disk
        shutil.rmtree(root)

        # First clean out the temp directory
        tmpdir = os.path.join(root, 'temp')
        if os.path.isdir(tmpdir):
            for tempname in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, tempname))

        # Upload the two-chunk file
        file = self._testUploadFile('helloWorld1.txt')

        # Test editing of the file info
        resp = self.request(path='/file/%s' % file['_id'], method='PUT',
                            user=self.user, params={'name': ' newName.json'})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], 'newName.json')
        file['name'] = resp.json['name']

        # We want to make sure the file got uploaded correctly into
        # the assetstore and stored at the right location
        hash = sha512(chunkData).hexdigest()
        self.assertEqual(hash, file['sha512'])
        self.assertFalse(os.path.isabs(file['path']))
        abspath = os.path.join(root, file['path'])

        self.assertTrue(os.path.isfile(abspath))
        self.assertEqual(os.stat(abspath).st_size, file['size'])

        # Make sure access control is enforced on download
        resp = self.request(
            path='/file/%s/download' % file['_id'], method='GET')
        self.assertStatus(resp, 401)

        # Make sure access control is enforced on get info
        resp = self.request(
            path='/file/' + str(file['_id']), method='GET')
        self.assertStatus(resp, 401)

        # Make sure we can get the file info and that it's filtered
        resp = self.request(
            path='/file/' + str(file['_id']), method='GET', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['mimeType'], 'text/plain')
        self.assertEqual(resp.json['exts'], ['json'])
        self.assertEqual(resp.json['_modelType'], 'file')
        self.assertEqual(resp.json['creatorId'], str(self.user['_id']))
        self.assertEqual(resp.json['size'], file['size'])
        self.assertTrue('itemId' in resp.json)
        self.assertTrue('assetstoreId' in resp.json)
        self.assertFalse('path' in resp.json)
        self.assertFalse('sha512' in resp.json)

        resp = self.request(
            path='/folder/%s/download' % self.privateFolder['_id'],
            method='GET')
        self.assertStatus(resp, 401)

        # Ensure the model layer raises an exception when trying to access
        # the file within a private folder
        self.assertRaises(AccessException, self.model('file').load, file['_id'])

        self._testDownloadFile(file, chunk1 + chunk2)
        self._testDownloadFolder()
        self._testDownloadCollection()

        # Test updating of the file contents
        newContents = 'test'
        resp = self.request(
            path='/file/%s/contents' % file['_id'], method='PUT',
            user=self.user, params={'size': len(newContents)})
        self.assertStatusOk(resp)

        # Old contents should not be immediately destroyed
        self.assertTrue(os.path.isfile(abspath))

        # Send the first chunk
        fields = (('offset', 0), ('uploadId', resp.json['_id']))
        files = (('chunk', 'newName.json', newContents),)
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)
        file = resp.json

        # Old contents should now be destroyed, new contents should be present
        self.assertFalse(os.path.isfile(abspath))
        abspath = os.path.join(root, file['path'])
        self.assertTrue(os.path.isfile(abspath))
        self._testDownloadFile(file, newContents)

        # Test updating an empty file
        resp = self.request(
            path='/file/%s/contents' % file['_id'], method='PUT',
            user=self.user, params={'size': 1})
        self.assertStatusOk(resp)

        self._testDeleteFile(file)
        self.assertFalse(os.path.isfile(abspath))

        # Upload two empty files to test duplication in the assetstore
        empty1 = self._testEmptyUpload('empty1.txt')
        empty2 = self._testEmptyUpload('empty2.txt')
        hash = sha512().hexdigest()
        abspath = os.path.join(root, empty1['path'])
        self.assertEqual((hash, hash), (empty1['sha512'], empty2['sha512']))
        self.assertTrue(os.path.isfile(abspath))
        self.assertEqual(os.stat(abspath).st_size, 0)

        self._testDownloadFile(empty1, '')

        # Deleting one of the duplicate files but not the other should
        # leave the file within the assetstore. Deleting both should remove it.

        self._testDeleteFile(empty1)
        self.assertTrue(os.path.isfile(abspath))
        self._testDeleteFile(empty2)
        self.assertFalse(os.path.isfile(abspath))

        # Test copying a file
        copyTestFile = self._testUploadFile('helloWorld1.txt')
        self._testCopyFile(copyTestFile)

    def testGridFsAssetstore(self):
        """
        Test usage of the GridFS assetstore type.
        """
        # Clear any old DB data
        base.dropGridFSDatabase('girder_test_file_assetstore')
        # Clear the assetstore database
        conn = getDbConnection()
        conn.drop_database('girder_test_file_assetstore')

        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        assetstore = self.model('assetstore').createGridFsAssetstore(
            name='Test', db='girder_test_file_assetstore')
        self.assetstore = assetstore

        chunkColl = conn['girder_test_file_assetstore']['chunk']

        # Upload the two-chunk file
        file = self._testUploadFile('helloWorld1.txt')
        hash = sha512(chunkData).hexdigest()
        self.assertEqual(hash, file['sha512'])

        # We should have two chunks in the database
        self.assertEqual(chunkColl.find({'uuid': file['chunkUuid']}).count(), 2)

        self._testDownloadFile(file, chunk1 + chunk2)
        self._testDownloadFolder()
        self._testDownloadCollection()

        # Delete the file, make sure chunks are gone from database
        self._testDeleteFile(file)
        self.assertEqual(chunkColl.find({'uuid': file['chunkUuid']}).count(), 0)

        empty = self._testEmptyUpload('empty.txt')
        self.assertEqual(sha512().hexdigest(), empty['sha512'])
        self._testDownloadFile(empty, '')
        self._testDeleteFile(empty)

        # Test copying a file
        copyTestFile = self._testUploadFile('helloWorld1.txt')
        self._testCopyFile(copyTestFile)

    @moto.mock_s3bucket_path
    def testS3Assetstore(self):
        botoParams = makeBotoConnectParams('access', 'secret')
        mock_s3.createBucket(botoParams, 'b')

        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        assetstore = self.model('assetstore').createS3Assetstore(
            name='test', bucket='b', accessKeyId='access', secret='secret',
            prefix='test')
        self.assetstore = assetstore

        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': 'hello.txt',
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)

        self.assertFalse(resp.json['s3']['chunked'])
        uploadId = resp.json['_id']
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'hello.txt', chunk1)]

        # Send the first chunk, we should get a 400
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Uploads of this length must be sent in a single chunk.')

        # Attempting to send second chunk with incorrect offset should fail
        fields = [('offset', 100), ('uploadId', uploadId)]
        files = [('chunk', 'hello.txt', chunk2)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Server has received 0 bytes, but client sent offset 100.')

        # Request offset from server (simulate a resume event)
        resp = self.request(path='/file/offset', method='GET', user=self.user,
                            params={'uploadId': uploadId})
        self.assertStatusOk(resp)

        # Trying to send too many bytes should fail
        currentOffset = resp.json['offset']
        fields = [('offset', resp.json['offset']), ('uploadId', uploadId)]
        files = [('chunk', 'hello.txt', "extra_"+chunk2+"_bytes")]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Received too many bytes.'
        })

        # The offset should not have changed
        resp = self.request(path='/file/offset', method='GET', user=self.user,
                            params={'uploadId': uploadId})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], currentOffset)

        # Send all in one chunk
        files = [('chunk', 'hello.txt', chunk1 + chunk2)]
        fields = [('offset', 0), ('uploadId', uploadId)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        file = self.model('file').load(resp.json['_id'], force=True)

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], self.assetstore['_id'])
        self.assertEqual(file['name'], 'hello.txt')
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        # Make sure metadata is updated in S3 when file info changes
        # (moto API doesn't cover this at all, so we manually mock.)
        with mock.patch('boto.s3.key.Key.set_remote_metadata') as m:
            resp = self.request(
                '/file/%s' % str(file['_id']), method='PUT', params={
                    'mimeType': 'application/csv',
                    'name': 'new name'
                }, user=self.user)
            self.assertEqual(len(m.mock_calls), 1)
            self.assertEqual(m.mock_calls[0][2], {
                'metadata_plus': {
                    'Content-Type': 'application/csv',
                    'Content-Disposition': b'attachment; filename="new name"'
                },
                'metadata_minus': [],
                'preserve_acl': True
            })

        # Enable testing of multi-chunk proxied upload
        S3AssetstoreAdapter.CHUNK_LEN = 5

        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': 'hello.txt',
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)
        self.assertTrue(resp.json['s3']['chunked'])

        uploadId = resp.json['_id']
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'hello.txt', chunk1)]

        # Send the first chunk, should now work
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        resp = self.request(path='/file/offset', user=self.user, params={
            'uploadId': uploadId
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], len(chunk1))

        # Hack: make moto accept our too-small chunks
        moto.s3.models.UPLOAD_PART_MIN_SIZE = 5

        # Send the second chunk
        files = [('chunk', 'hello.txt', chunk2)]
        fields = [('offset', resp.json['offset']), ('uploadId', uploadId)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        file = resp.json

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], str(self.assetstore['_id']))
        self.assertEqual(file['name'], 'hello.txt')
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        # Test copying a file ( we don't assert to content in the case because
        # the S3 download will fail )
        self._testCopyFile(file, assertContent=False)

    def testLinkFile(self):
        params = {
            'parentType': 'folder',
            'parentId': self.privateFolder['_id'],
            'name': 'My Link Item',
            'linkUrl': 'javascript:alert("x");'
        }

        # Try to create a link file with a disallowed URL, should be rejected
        resp = self.request(
            path='/file', method='POST', user=self.user, params=params)
        self.assertValidationError(resp, 'linkUrl')

        # Create a valid link file
        params['linkUrl'] = ' http://www.google.com  '
        resp = self.request(
            path='/file', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        file = resp.json
        self.assertEqual(file['assetstoreId'], None)
        self.assertEqual(file['name'], 'My Link Item')
        self.assertEqual(file['linkUrl'], params['linkUrl'].strip())

        # Attempt to download the link file, make sure we are redirected
        resp = self.request(
            path='/file/%s/download' % file['_id'], method='GET',
            isJson=False, user=self.user)
        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'], params['linkUrl'].strip())

        # Download containing folder as zip file
        resp = self.request(
            path='/folder/%s/download' % self.privateFolder['_id'],
            method='GET', user=self.user, isJson=False)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        body = self.getBody(resp, text=False)
        zip = zipfile.ZipFile(io.BytesIO(body), 'r')
        self.assertTrue(zip.testzip() is None)

        # The file should just contain the URL of the link
        extracted = zip.read('Private/My Link Item').decode('utf8')
        self.assertEqual(extracted, params['linkUrl'].strip())

    def tearDown(self):
        if self.testForFinalizeUpload:
            self.assertTrue(self.finalizeUploadBeforeCalled)
            self.assertTrue(self.finalizeUploadAfterCalled)

            events.unbind('model.file.finalizeUpload.before',
                          '_testFinalizeUploadBefore')
            events.unbind('model.file.finalizeUpload.after',
                          '_testFinalizeUploadAfter')
