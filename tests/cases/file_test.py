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

from bson.objectid import ObjectId
from hashlib import sha512
from .. import base

from girder.constants import AccessType, ROOT_DIR


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


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
        self.assetstore = self.model('assetstore').getCurrent()

    def _testEmptyUpload(self):
        """
        Uploads an empty file to the server.
        """
        pass

    def _testUploadFile(self):
        """
        Uploads a non-empty file to the server.
        """
        chunk1, chunk2 = ('hello ', 'world')
        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.privateFolder['_id'],
                'name': 'helloWorld.txt',
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
        files = [('chunk', 'helloWorld.txt', chunk2)]
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

        self.assertEqual(self.model('assetstore').getCurrent()['_id'],
                         ObjectId(file['assetstoreId']))
        self.assertEqual(file['name'], 'helloWorld.txt')
        self.assertEqual(file['size'], len(chunk1 + chunk2))

        return file

    def _testDownloadFile(self, file):
        """
        Downloads the previously uploaded file from the server.
        """
        pass

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
        self.model('assetstore').remove(self.assetstore)
        assetstore = self.model('assetstore').createFilesystemAssetstore(
            name='Test', root=root)

        self._testEmptyUpload()

        file = self._testUploadFile()

        # We want to make sure the file got uploaded correctly into
        # the assetstore and stored at the right location
        hash = sha512('hello world').hexdigest()
        self.assertEqual(hash, file['sha512'])
        path = os.path.join(root, file['path'])
        self.assertTrue(os.path.isfile(path))

        self._testDownloadFile(file)

        self._testDeleteFile(file)
        self.assertFalse(os.path.isfile(path))
