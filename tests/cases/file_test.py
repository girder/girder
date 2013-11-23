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

import cherrypy
import json
import os

from hashlib import sha512
from .. import base

from girder.constants import AccessType, ROOT_DIR


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()

chunk1, chunk2 = ('hello ', 'world')


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

        return file

    def _testUploadFile(self, name):
        """
        Uploads a non-empty file to the server.
        """
        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': name,
                'size': len(chunk1) + len(chunk2)
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the first chunk
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'helloWorld.txt', chunk1)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Attempting to send second chunk with incorrect offset should fail
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', name, chunk2)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.user, fields=fields, files=files)
        self.assertStatus(resp, 400)

        # Request offset from server (simulate a resume event)
        resp = self.request(path='/file/offset', method='GET', user=self.user,
                            params={'uploadId': uploadId})
        self.assertStatusOk(resp)

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

        self.assertEqual(contents, resp.collapse_body())

    def _testDeleteFile(self, file):
        """
        Deletes the previously uploaded file from the server.
        """
        resp = self.request(
            path='/file/%s' % str(file['_id']), method='DELETE', user=self.user)
        self.assertStatusOk(resp)

    def testFilesystemAssetstore(self):
        """
        Test usage of the Filesystem assetstore type.
        """
        root = os.path.join(ROOT_DIR, 'tests', 'assetstore')
        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        assetstore = self.model('assetstore').createFilesystemAssetstore(
            name='Test', root=root)
        self.assetstore = assetstore

        # First clean out the temp directory
        for tempname in os.listdir(os.path.join(root, 'temp')):
            os.remove(os.path.join(root, 'temp', tempname))

        # Upload the two-chunk file
        file = self._testUploadFile('helloWorld1.txt')

        # We want to make sure the file got uploaded correctly into
        # the assetstore and stored at the right location
        hash = sha512(chunk1 + chunk2).hexdigest()
        self.assertEqual(hash, file['sha512'])
        self.assertFalse(os.path.isabs(file['path']))
        abspath = os.path.join(root, file['path'])

        self.assertTrue(os.path.isfile(abspath))
        self.assertEqual(os.stat(abspath).st_size, file['size'])

        self._testDownloadFile(file, chunk1 + chunk2)

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
