# -*- coding: utf-8 -*-
import boto3
import httmock
import io
import json
import moto
import os
import shutil
import urllib.parse
import zipfile

from hashlib import sha512
from .. import base, mock_s3

from girder import events
from girder.models import getDbConnection
from girder.exceptions import AccessException, GirderException, FilePathException
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey
from girder.utility import gridfs_assetstore_adapter
from girder.utility.filesystem_assetstore_adapter import DEFAULT_PERMS
from girder.utility.s3_assetstore_adapter import makeBotoConnectParams, S3AssetstoreAdapter

# The latest moto/boto/botocore requires dummy credentials to function.  It is unclear if
# this is a bug or intended behavior.
#  https://github.com/spulec/moto/issues/1793#issuecomment-431459262
#  https://github.com/spulec/moto/issues/1924
os.environ['AWS_ACCESS_KEY_ID'] = 'access'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'secret'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


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
        super().setUp()

        user = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.user = User().createUser(**user)
        folders = Folder().childFolders(
            parent=self.user, parentType='user', user=self.user)
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder
        secondUser = {
            'email': 'second@girder.test',
            'login': 'secondlogin',
            'firstName': 'Second',
            'lastName': 'User',
            'password': 'secondpassword'
        }
        self.secondUser = User().createUser(**secondUser)

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

        return File().load(file['_id'], force=True)

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
        resp = self.request(
            path='/file/chunk', method='POST', body=chunk1, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatus(resp, 401)

        # Uploading with the wrong user should fail
        resp = self.request(
            path='/file/chunk', method='POST', body=chunk1, user=self.secondUser, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatus(resp, 403)

        # Sending the first chunk should fail because the default minimum chunk
        # size is larger than our chunk.
        Setting().unset(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE)
        resp = self.request(
            path='/file/chunk', method='POST', body=chunk1, user=self.user, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Chunk is smaller than the minimum size.'
        })

        # Send the first chunk
        Setting().set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 0)
        resp = self.request(
            path='/file/chunk', method='POST', body=chunk1, user=self.user, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)

        # Attempting to send second chunk with incorrect offset should fail
        resp = self.request(
            path='/file/chunk', method='POST', body=chunk2, user=self.user, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatus(resp, 400)

        # Ask for completion before sending second chunk should fail
        resp = self.request(path='/file/completion', method='POST',
                            user=self.user, params={'uploadId': uploadId})
        self.assertStatus(resp, 400)

        # Request offset from server (simulate a resume event)
        resp = self.request(
            path='/file/offset', user=self.user, params={'uploadId': uploadId})
        self.assertStatusOk(resp)

        # Trying to send too many bytes should fail
        currentOffset = resp.json['offset']
        resp = self.request(
            path='/file/chunk', method='POST', body='extra_' + chunk2 + '_bytes', params={
                'offset': currentOffset,
                'uploadId': uploadId
            }, user=self.user, type='text/plain')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Received too many bytes.'
        })

        # The offset should not have changed
        resp = self.request(
            path='/file/offset', user=self.user, params={'uploadId': uploadId})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], currentOffset)

        # Now upload the second chunk
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=chunk2, params={
                'offset': resp.json['offset'],
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)

        file = resp.json

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], str(self.assetstore['_id']))
        self.assertEqual(file['name'], name)
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        return file

    def _testDownloadFile(self, file, contents, contentDisposition=None):
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
        if not contentDisposition:
            contentDisposition = 'filename="%s"' % file['name']
        if contents:
            self.assertEqual(resp.headers['Content-Type'],
                             'text/plain;charset=utf-8')
            self.assertEqual(resp.headers['Content-Disposition'],
                             'attachment; %s' % contentDisposition)
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
                             'inline; %s' % contentDisposition)
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
                urllib.parse.quote(file['name'].encode('utf8'))
            ), method='GET', user=self.user, isJson=False)
        self.assertStatusOk(resp)
        if contents:
            self.assertEqual(resp.headers['Content-Type'],
                             'text/plain;charset=utf-8')
        self.assertEqual(contents, self.getBody(resp))
        # test the file context as part of the download test
        self._testFileContext(file, contents)

    def _testFileContext(self, file, contents):
        """
        Test the python file context handler.

        :param file: The file object to test.
        :type file: dict
        :param contents: The expected contents.
        :type contents: str
        """
        def _readFile(handle):
            buf = b''
            while True:
                chunk = handle.read(32768)
                buf += chunk
                if not chunk:
                    break
            return buf

        # Test reading via the model layer file-like API
        contents = contents.encode('utf8')
        with File().open(file) as handle:
            self.assertEqual(handle.tell(), 0)
            handle.seek(0)
            buf = _readFile(handle)
            self.assertEqual(buf, contents)

            # Test seek modes
            handle.seek(2)
            buf = _readFile(handle)
            self.assertEqual(buf, contents[2:])

            handle.seek(2)
            handle.seek(2, os.SEEK_CUR)
            buf = _readFile(handle)
            self.assertEqual(buf, contents[4:])

            handle.seek(-2, os.SEEK_END)
            buf = _readFile(handle)
            self.assertEqual(buf, contents[-2:])

            handle.seek(2, os.SEEK_END)
            buf = _readFile(handle)
            self.assertEqual(buf, b'')

            # Read without a length parameter
            handle.seek(0, os.SEEK_SET)
            buf = handle.read()
            self.assertEqual(buf, contents)

            handle.seek(-2, os.SEEK_END)
            buf = handle.read()
            self.assertEqual(buf, contents[-2:])

            # Read with a negative length parameter
            handle.seek(0, os.SEEK_SET)
            buf = handle.read(-1)
            self.assertEqual(buf, contents)

            handle.seek(-2, os.SEEK_END)
            buf = handle.read(-5)
            self.assertEqual(buf, contents[-2:])

            # Read too many bytes on files long enough to test
            if len(contents) > 6:
                handle._maximumReadSize = 6
                handle.seek(0, os.SEEK_SET)
                self.assertRaises(GirderException, handle.read, 7)
                handle.seek(0, os.SEEK_SET)
                self.assertRaises(GirderException, handle.read)
                handle.seek(-2, os.SEEK_END)
                buf = handle.read()
                self.assertEqual(buf, contents[-2:])

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
        resp = self.request(
            path='/file/chunk', method='POST', body=contents, user=self.user, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)

        # List files in the folder
        testFolder = Folder().load(test['_id'], force=True)
        fileList = [(path, file['name'])
                    for (path, file) in Folder().fileList(
                        testFolder, user=self.user,
                        subpath=True, data=False)]
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
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=contents, params={
                'uploadId': uploadId
            }, type='text/plain')
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
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=contents, params={
                'uploadId': uploadId
            }, type='application/octet-stream')
        self.assertStatusOk(resp)

        # Download the collection
        path = '/collection/%s/download' % collection['_id']
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
        collection = Collection().load(collection['_id'], force=True)
        collection['public'] = True
        collection = Collection().save(collection)

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
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=contents, params={
                'uploadId': uploadId
            }, type='application/octet-stream')
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
                            method='POST', params=params, user=self.user)
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
        self.assetstore = Assetstore().getCurrent()
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

        # Make sure internal details got filtered
        self.assertNotIn('sha512', file)
        self.assertNotIn('path', file)
        self.assertEqual(file['_modelType'], 'file')

        file = File().load(file['_id'], force=True)

        # We want to make sure the file got uploaded correctly into
        # the assetstore and stored at the right location
        hash = sha512(chunkData).hexdigest()
        self.assertEqual(hash, file['sha512'])
        self.assertFalse(os.path.isabs(file['path']))
        abspath = os.path.join(root, file['path'])

        self.assertTrue(os.path.isfile(abspath))
        self.assertEqual(os.stat(abspath).st_size, file['size'])
        self.assertEqual(os.stat(abspath).st_mode & 0o777, DEFAULT_PERMS)

        # Make sure the file reports the same path as we have
        self.assertEqual(File().getAssetstoreAdapter(file).fullPath(file), abspath)
        self.assertEqual(File().getLocalFilePath(file), abspath)

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
        self.assertRaises(AccessException, File().load, file['_id'])

        self._testDownloadFile(file, chunk1 + chunk2)
        self._testDownloadFolder()
        self._testDownloadCollection()

        # Change file permissions for the assetstore
        params = {
            'name': 'test assetstore',
            'root': root,
            'current': True,
            'perms': '732'
        }
        resp = self.request(path='/assetstore/%s' % self.assetstore['_id'],
                            method='PUT', user=self.user, params=params)
        self.assertStatusOk(resp)

        # Test updating of the file contents
        newContents = 'test'
        resp = self.request(
            path='/file/%s/contents' % file['_id'], method='PUT',
            user=self.user, params={'size': len(newContents)})
        self.assertStatusOk(resp)

        # Old contents should not be immediately destroyed
        self.assertTrue(os.path.isfile(abspath))

        # Send the first chunk
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=newContents, params={
                'uploadId': resp.json['_id']
            }, type='application/octet-stream')
        self.assertStatusOk(resp)
        file = File().load(resp.json['_id'], force=True)

        # Old contents should now be destroyed, new contents should be present
        self.assertFalse(os.path.isfile(abspath))
        abspath = os.path.join(root, file['path'])
        self.assertTrue(os.path.isfile(abspath))
        self._testDownloadFile(file, newContents)

        # Make sure new permissions are respected
        self.assertEqual(os.stat(abspath).st_mode & 0o777, 0o732)

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

        # Test unicode filenames for content disposition.  The test name has
        # quotes, a Linear-B codepoint, Cyrllic, Arabic, Chinese, and an emoji.
        filename = u'Unicode "sample" \U00010088 ' + \
                   u'\u043e\u0431\u0440\u0430\u0437\u0435\u0446 ' + \
                   u'\u0639\u064a\u0646\u0629 \u6a23\u54c1 \U0001f603'
        file = self._testUploadFile(filename)
        file = File().load(file['_id'], force=True)
        testval = 'filename="Unicode \\"sample\\"     "; filename*=UTF-8\'\'' \
            'Unicode%20%22sample%22%20%F0%90%82%88%20%D0%BE%D0%B1%D1%80%D0' \
            '%B0%D0%B7%D0%B5%D1%86%20%D8%B9%D9%8A%D9%86%D8%A9%20%E6%A8%A3%E5' \
            '%93%81%20%F0%9F%98%83'
        self._testDownloadFile(file, chunk1 + chunk2, testval)

    def testGridFsAssetstore(self):
        """
        Test usage of the GridFS assetstore type.
        """
        # Must also lower GridFS's internal chunk size to support our small chunks
        gridfs_assetstore_adapter.CHUNK_SIZE, old = 6, gridfs_assetstore_adapter.CHUNK_SIZE

        # Clear any old DB data
        base.dropGridFSDatabase('girder_test_file_assetstore')
        # Clear the assetstore database
        conn = getDbConnection()
        conn.drop_database('girder_test_file_assetstore')

        Assetstore().remove(Assetstore().getCurrent())
        assetstore = Assetstore().createGridFsAssetstore(
            name='Test', db='girder_test_file_assetstore')
        self.assetstore = assetstore

        chunkColl = conn['girder_test_file_assetstore']['chunk']

        # Upload the two-chunk file
        file = self._testUploadFile('helloWorld1.txt')
        hash = sha512(chunkData).hexdigest()
        file = File().load(file['_id'], force=True)
        self.assertEqual(hash, file['sha512'])

        # The file should have no local path
        self.assertRaises(FilePathException, File().getLocalFilePath, file)

        # We should have two chunks in the database
        self.assertEqual(chunkColl.find({'uuid': file['chunkUuid']}).count(), 2)

        self._testDownloadFile(file, chunk1 + chunk2)

        # Reset chunk size so the large file testing isn't horribly slow
        gridfs_assetstore_adapter.CHUNK_SIZE = old

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

    @moto.mock_s3
    def testS3Assetstore(self):
        botoParams = makeBotoConnectParams('access', 'secret')
        mock_s3.createBucket(botoParams, 'bname')

        Assetstore().remove(Assetstore().getCurrent())
        assetstore = Assetstore().createS3Assetstore(
            name='test', bucket='bname', accessKeyId='access', secret='secret',
            prefix='test', serverSideEncryption=True)
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

        # Send the first chunk, we should get a 400
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=chunk1, params={
                'uploadId': uploadId
            }, type='application/octet-stream')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Uploads of this length must be sent in a single chunk.')

        # Attempting to send second chunk with incorrect offset should fail
        resp = self.request(
            path='/file/chunk', method='POST', user=self.user, body=chunk2, params={
                'offset': 100,
                'uploadId': uploadId
            }, type='application/octet-stream')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Server has received 0 bytes, but client sent offset 100.')

        # Request offset from server (simulate a resume event)
        resp = self.request(
            path='/file/offset', method='GET', user=self.user, params={'uploadId': uploadId})
        self.assertStatusOk(resp)

        initRequests = []

        @httmock.all_requests
        def mockChunkUpload(url, request):
            """
            We used to be able to use moto to mock the sending of chunks to
            S3, however we now no longer use the boto API to do so internally,
            and must mock this out at the level of requests.
            """
            if url.netloc != 'bname.s3.amazonaws.com':
                raise Exception('Unexpected request to host ' + url.netloc)

            body = request.body.read(65536)  # sufficient for now, we have short bodies

            if 'x-amz-meta-uploader-ip' in url.query:
                # this is an init request, not a chunk upload
                initRequests.append(request)

            # Actually set the key in moto
            self.assertTrue(url.path.startswith('/test/'))
            client = boto3.client('s3')
            client.put_object(Bucket='bname', Key=url.path[1:], Body=body)

            return {
                'status_code': 200
            }

        # Trying to send too many bytes should fail
        currentOffset = resp.json['offset']
        with httmock.HTTMock(mockChunkUpload):
            resp = self.request(
                path='/file/chunk', method='POST', body='extra_' + chunk2 + '_bytes', params={
                    'offset': currentOffset,
                    'uploadId': uploadId
                }, user=self.user, type='application/octet-stream')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'message': 'Received too many bytes.'
        })
        self.assertEqual(len(initRequests), 1)
        self.assertEqual(initRequests[-1].headers['x-amz-server-side-encryption'], 'AES256')

        # The offset should not have changed
        resp = self.request(
            path='/file/offset', method='GET', user=self.user, params={'uploadId': uploadId})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], currentOffset)

        # Send all in one chunk
        with httmock.HTTMock(mockChunkUpload):
            resp = self.request(
                path='/file/chunk', method='POST', body=chunk1 + chunk2, user=self.user, params={
                    'uploadId': uploadId
                }, type='application/octet-stream')
        self.assertStatusOk(resp)
        self.assertEqual(len(initRequests), 2)
        self.assertEqual(initRequests[-1].headers['x-amz-server-side-encryption'], 'AES256')

        file = File().load(resp.json['_id'], force=True)

        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], self.assetstore['_id'])
        self.assertEqual(file['name'], 'hello.txt')
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        resp = self.request('/file/%s' % file['_id'], method='PUT', params={
            'mimeType': 'application/csv',
            'name': 'new name'
        }, user=self.user)
        self.assertStatusOk(resp)

        # Make sure our metadata got updated in S3
        obj = boto3.client('s3').get_object(Bucket='bname', Key=file['s3Key'])
        self.assertEqual(obj['ContentDisposition'], 'attachment; filename="new name"')
        self.assertEqual(obj['ContentType'], 'application/csv')

        # Test with SSE disabled
        self.assetstore['serverSideEncryption'] = False
        self.assetstore = Assetstore().save(self.assetstore)
        initRequests = []

        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': 'hello.txt',
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        with httmock.HTTMock(mockChunkUpload):
            resp = self.request(
                path='/file/chunk', method='POST', body=chunk1 + chunk2, user=self.user, params={
                    'uploadId': uploadId
                }, type='application/octet-stream')
        self.assertStatusOk(resp)
        self.assertEqual(len(initRequests), 1)
        self.assertNotIn('x-amz-server-side-encryption', initRequests[0].headers)

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

        # Send the first chunk, should now work
        with httmock.HTTMock(mockChunkUpload):
            resp = self.request(
                path='/file/chunk', method='POST', body=chunk1, user=self.user, params={
                    'uploadId': uploadId
                }, type='application/octet-stream')
        self.assertStatusOk(resp)

        resp = self.request(path='/file/offset', user=self.user, params={
            'uploadId': uploadId
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], len(chunk1))

        # Hack: make moto accept our too-small chunks
        moto.s3.models.UPLOAD_PART_MIN_SIZE = 5

        # Send the second chunk
        with httmock.HTTMock(mockChunkUpload):
            resp = self.request(
                path='/file/chunk', method='POST', user=self.user, body=chunk2, params={
                    'offset': resp.json['offset'],
                    'uploadId': uploadId
                }, type='text/plain')
        self.assertStatusOk(resp)

        file = resp.json

        self.assertEqual(file['_modelType'], 'file')
        self.assertHasKeys(file, ['itemId'])
        self.assertEqual(file['assetstoreId'], str(self.assetstore['_id']))
        self.assertEqual(file['name'], 'hello.txt')
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        # Test copying a file ( we don't assert to content in the case because
        # the S3 download will fail )
        self._testCopyFile(file, assertContent=False)

        # The file we get back from the rest call doesn't have the s3Key value,
        # so reload the file from the database
        file = File().load(file['_id'], force=True)

        # Mock Serve range requests
        @httmock.urlmatch(netloc=r'^bname.s3.amazonaws.com')
        def s3_range_mock(url, request):
            data = chunk1 + chunk2
            if request.headers.get('range', '').startswith('bytes='):
                start, end = request.headers['range'].split('bytes=')[1].split('-')
                data = data[int(start):int(end) + 1]
            return data

        with httmock.HTTMock(s3_range_mock):
            self._testFileContext(file, chunk1 + chunk2)

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

        # The file should report no assetstore adapter
        fileDoc = File().load(file['_id'], force=True)
        self.assertIsNone(File().getAssetstoreAdapter(fileDoc))

    def tearDown(self):
        if self.testForFinalizeUpload:
            self.assertTrue(self.finalizeUploadBeforeCalled)
            self.assertTrue(self.finalizeUploadAfterCalled)

        events.unbind('model.file.finalizeUpload.before', '_testFinalizeUploadBefore')
        events.unbind('model.file.finalizeUpload.after', '_testFinalizeUploadAfter')
