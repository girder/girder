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

import os
import io
import json
import shutil
import zipfile

from .. import base

from girder.constants import AccessType, ROOT_DIR


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ItemTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        # Create a set of users so we can have some folders.
        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

        folders = self.model('folder').childFolders(
            self.users[0], 'user', user=self.users[0])
        (self.publicFolder, self.privateFolder) = folders

        root = os.path.join(ROOT_DIR, 'tests', 'assetstore')
        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        assetstore = self.model('assetstore').createFilesystemAssetstore(
            name='Test', root=root)
        self.assetstore = assetstore

        # Clean out the test assetstore on disk
        shutil.rmtree(assetstore['root'])

        # First clean out the temp directory
        tmpdir = os.path.join(root, 'temp')
        if os.path.isdir(tmpdir):
            for tempname in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, tempname))

    def _createItem(self, parentId, name, description, user):
        params = {
            'name': name,
            'description': description,
            'folderId': parentId
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=user)
        self.assertStatusOk(resp)
        return resp.json

    def _testUploadFileToItem(self, item, name, user, contents):
        """
        Uploads a non-empty file to the server.
        """
        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=user, params={
                'parentType': 'item',
                'parentId': item['_id'],
                'name': name,
                'size': len(contents)
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the first chunk
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', name, contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=user, fields=fields, files=files)
        self.assertStatusOk(resp)

    def _testDownloadSingleFileItem(self, item, user, contents):
        """
        Downloads a single-file item from the server
        :param item: The item to download.
        :type item: dict
        :param contents: The expected contents.
        :type contents: str
        """
        resp = self.request(path='/item/{}/download'.format(item['_id']),
                            method='GET', user=user, isJson=False)
        self.assertStatusOk(resp)

        self.assertEqual(contents, resp.collapse_body())

        # Test downloading with an offset
        resp = self.request(path='/item/{}/download'.format(item['_id']),
                            method='GET', user=user, isJson=False,
                            params={'offset': 1})
        self.assertStatusOk(resp)

        self.assertEqual(contents[1:], resp.collapse_body())

    def _testDownloadMultiFileItem(self, item, user, contents):
        resp = self.request(path='/item/{}/download'.format(item['_id']),
                            method='GET', user=user, isJson=False)
        self.assertStatusOk(resp)
        zipFile = zipfile.ZipFile(io.BytesIO(resp.collapse_body()), 'r')
        filesInItem = zipFile.namelist()
        self.assertEqual(zipFile.read(filesInItem[0]), contents[0])
        self.assertEqual(zipFile.read(filesInItem[1]), contents[1])

    def testItemDownloadAndChildren(self):
        curItem = self._createItem(self.publicFolder['_id'],
                                   'test_for_download', 'fake description',
                                   self.users[0])
        self._testUploadFileToItem(curItem, 'file_1', self.users[0], 'foobar')

        self._testDownloadSingleFileItem(curItem, self.users[0], 'foobar')

        self._testUploadFileToItem(curItem, 'file_2', self.users[0], 'foobz')

        resp = self.request(path='/item/{}/files'.format(curItem['_id']),
                            method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['name'], 'file_1')
        self.assertEqual(resp.json[1]['name'], 'file_2')
        self.assertEqual(resp.json[0]['size'], 6)
        self.assertEqual(resp.json[1]['size'], 5)

        self._testDownloadMultiFileItem(curItem, self.users[0],
                                        ('foobar', 'foobz'))

    def testItemCrud(self):
        """
        Test Create, Read, Update, and Delete of items.
        """
        self.ensureRequiredParams(
            path='/item', method='POST', required=('name', 'folderId'))

        # Attempt to create an item without write permission, should fail
        params = {
            'name': ' ',
            'description': ' a description ',
            'folderId': self.publicFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # Shouldn't be allowed to have an empty name
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertValidationError(resp, 'name')

        # Actually create the item in user 0's private folder
        params['name'] = ' my item name'
        params['folderId'] = self.privateFolder['_id']
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)

        item = resp.json
        self.assertEqual(item['name'], params['name'].strip())
        self.assertEqual(item['description'], params['description'].strip())

        # User 1 should not be able to see the item via find by folderId
        params = {
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='GET', user=self.users[1],
                            params=params)
        self.assertStatus(resp, 403)

        # Or by just requesting the item itself by ID
        resp = self.request(path='/item/%s' % str(item['_id']), method='GET',
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # User 0 should be able to see the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='GET',
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], item['_id'])

        # Also from the children call
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])

        # Test update of the item
        params = {
            'name': 'changed name',
            'description': 'new description'
        }
        resp = self.request(path='/item/{}'.format(item['_id']), method='PUT',
                            params=params, user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'])
        self.assertEqual(resp.json['description'], params['description'])

        # Try to update/PUT without an id
        resp = self.request(path='/item/', method='PUT',
                            params=params, user=self.users[0])
        self.assertStatus(resp, 400)

        # Try a bad endpoint (should 400)
        resp = self.request(path='/item/{}/blurgh'.format(item['_id']),
                            method='GET',
                            user=self.users[1])
        self.assertStatus(resp, 400)

        # Try delete with no ID (should 400)
        resp = self.request(path='/item/', method='DELETE', user=self.users[1])
        self.assertStatus(resp, 400)

        # User 1 should not be able to delete the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # User 0 should be able to delete the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[0])
        self.assertStatusOk(resp)

        # Verify that the item is deleted
        item = self.model('item').load(item['_id'])
        self.assertEqual(item, None)

    def testItemMetadataCrud(self):
        """
        Test CRUD of metadata.
        """

        # Create an item
        params = {
            'name': 'item with metadata',
            'description': ' a description ',
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        item = resp.json

        # Add some metadata
        metadata = {
            'foo': 'bar',
            'test': 2
        }
        resp = self.request(path='/item/{}/metadata'.format(item['_id']),
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['foo'], metadata['foo'])
        self.assertEqual(item['meta']['test'], metadata['test'])

        # Edit and remove metadata
        metadata['test'] = None
        metadata['foo'] = 'baz'
        resp = self.request(path='/item/{}/metadata'.format(item['_id']),
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['foo'], metadata['foo'])
        self.assertNotHasKeys(item['meta'], ['test'])
