#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

from girder.constants import SettingKey
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder.models.user import User
from tests import base

from girder_authorized_upload.constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD


def setUpModule():
    base.enabledPlugins.append('authorized_upload')
    base.startServer()


def tearDownModule():
    base.stopServer()


class AuthorizedUploadTest(base.TestCase):
    def setUp(self):
        super(AuthorizedUploadTest, self).setUp()

        self.admin = User().createUser(
            login='admin',
            password='passwd',
            firstName='admin',
            lastName='admin',
            email='admin@admin.org'
        )

        for folder in Folder().childFolders(parent=self.admin, parentType='user', user=self.admin):
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

    def testAuthorizedUpload(self):
        Setting().set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 1)

        # Anon access should not work
        resp = self.request('/authorized_upload', method='POST', params={
            'folderId': self.privateFolder['_id']
        })
        self.assertStatus(resp, 401)

        # Create our secure URL
        resp = self.request('/authorized_upload', method='POST', user=self.admin, params={
            'folderId': self.privateFolder['_id']
        })
        self.assertStatusOk(resp)
        parts = resp.json['url'].rsplit('/', 3)
        tokenId, folderId = parts[-1], parts[-2]

        token = Token().load(tokenId, force=True, objectId=False)

        self.assertIsNotNone(token)
        self.assertEqual(folderId, str(self.privateFolder['_id']))
        self.assertEqual(set(token['scope']), {
            TOKEN_SCOPE_AUTHORIZED_UPLOAD,
            'authorized_upload_folder_%s' % self.privateFolder['_id']
        })

        # Make sure this token doesn't let us upload into a different folder
        params = {
            'parentType': 'folder',
            'parentId': self.publicFolder['_id'],
            'name': 'hello.txt',
            'size': 11,
            'mimeType': 'text/plain'
        }

        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatus(resp, 401)

        # Initialize upload into correct folder
        params['parentId'] = self.privateFolder['_id']
        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatusOk(resp)

        # We should remove the scope that allows further uploads
        upload = Upload().load(resp.json['_id'])
        token = Token().load(tokenId, force=True, objectId=False)
        self.assertEqual(token['scope'], [
            'authorized_upload_folder_%s' % self.privateFolder['_id']
        ])

        # Authorized upload ID should be present in the token
        self.assertEqual(token['authorizedUploadId'], upload['_id'])

        # Attempting to initialize new uploads using the token should fail
        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatus(resp, 401)

        # Uploading a chunk should work with the token
        fields = [('offset', 0), ('uploadId', str(upload['_id']))]
        files = [('chunk', 'hello.txt', 'hello ')]
        resp = self.multipartRequest(path='/file/chunk', token=tokenId, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Requesting our offset should work with the token
        # The offset should not have changed
        resp = self.request(path='/file/offset', method='GET', token=tokenId, params={
            'uploadId': upload['_id']
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], 6)

        # Upload the second chunk
        fields = [('offset', 6), ('uploadId', str(upload['_id']))]
        files = [('chunk', 'hello.txt', 'world')]
        resp = self.multipartRequest(path='/file/chunk', token=tokenId, fields=fields, files=files)
        self.assertStatusOk(resp)

        # Trying to upload more chunks should fail
        fields = [('offset', 11), ('uploadId', str(upload['_id']))]
        files = [('chunk', 'hello.txt', 'more bytes')]
        resp = self.multipartRequest(path='/file/chunk', token=tokenId, fields=fields, files=files)
        self.assertStatus(resp, 401)

        # The token should be destroyed
        self.assertIsNone(Token().load(tokenId, force=True, objectId=False))
