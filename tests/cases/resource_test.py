#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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
import os
import zipfile

from .. import base

from girder.constants import AccessType
from girder.models.notification import ProgressState


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class FolderTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.admin = self.model('user').createUser(**admin)

    def _createFiles(self):
        """
        Create a set of items, folders, files, metadata, and collections for
        testing.
        """
        self.expectedZip = {}
        # Create a collection
        coll = {
            'name': 'Test Collection',
            'description': 'The description',
            'public': True,
            'creator': self.admin
        }
        self.collection = self.model('collection').createCollection(**coll)
        # Get the collection's folder
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'collection',
                'parentId': self.collection['_id'],
            })
        self.collectionPrivateFolder = resp.json[0]
        # Get the admin user's folders
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        self.adminPrivateFolder = resp.json[0]
        self.adminPublicFolder = resp.json[1]
        # Create a folder within the admin public forlder
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': 'Folder 1', 'parentId': self.adminPublicFolder['_id']
            })
        self.adminSubFolder = resp.json
        # Create a series of items
        self.items = []
        self.items.append(self.model('item').createItem(
            'Item 1', self.admin, self.adminPublicFolder))
        self.items.append(self.model('item').createItem(
            'Item 2', self.admin, self.adminPublicFolder))
        self.items.append(self.model('item').createItem(
            'Item 3', self.admin, self.adminSubFolder))
        self.items.append(self.model('item').createItem(
            'Item 4', self.admin, self.collectionPrivateFolder))
        # Upload a series of files
        file, path, contents = self._uploadFile('File 1', self.items[0])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 2', self.items[0])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 3', self.items[1])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 4', self.items[2])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 5', self.items[3])
        self.expectedZip[path] = contents
        # place some metadata on one of the items and one of the folders
        meta = {'key': 'value'}
        self.model('item').setMetadata(self.items[2], meta)
        parents = self.model('item').parentsToRoot(self.items[2], self.admin)
        path = os.path.join(*([part['object'].get('name',
            part['object'].get('login', '')) for part in parents] +
            [self.items[2]['name'], 'metadata.json']))
        self.expectedZip[path] = json.dumps(meta)

        meta = {'key2': 'value2'}
        self.model('folder').setMetadata(self.adminPublicFolder, meta)
        parents = self.model('folder').parentsToRoot(self.adminPublicFolder,
                                                     user=self.admin)
        path = os.path.join(*([part['object'].get('name',
            part['object'].get('login', '')) for part in parents] +
            [self.adminPublicFolder['name'], 'metadata.json']))
        self.expectedZip[path] = json.dumps(meta)

    def _uploadFile(self, name, item):
        """
        Upload a random file to an item.
        :param name: name of the file.
        :param item: item to upload the file to.
        :returns: file: the created file object
                  path: the path to the file within the parent hierarchy.
                  contents: the contents that were generated for the file.
        """
        contents = os.urandom(1024)
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'item',
                'parentId': item['_id'],
                'name': name,
                'size': len(contents),
                'mimeType': 'application/octet-stream'
            })
        self.assertStatusOk(resp)
        upload = resp.json
        fields = [('offset', 0), ('uploadId', upload['_id'])]
        files = [('chunk', name, contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.admin, fields=fields, files=files)
        self.assertStatusOk(resp)
        file = resp.json
        parents = self.model('item').parentsToRoot(item, user=self.admin)
        path = os.path.join(*([part['object'].get('name',
            part['object'].get('login', '')) for part in parents] +
            [item['name'], name]))
        return (file, path, contents)

    def testDownloadResources(self):
        self._createFiles()
        resourceList = {
            'collection': [str(self.collection['_id'])],
            'user': [str(self.admin['_id'])]
            }
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps(resourceList),
                'includeMetadata': True
            }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(resp.collapse_body()), 'r')
        import sys ##DWM::
        sys.stderr.write(repr(resp.collapse_body())+"\n") ##DWM::
        self.assertTrue(zip.testzip() is None)
        import sys ##DWM::
        sys.stderr.write(str(len([name for name in zip.namelist()]))+"\n") ##DWM::
        for name in zip.namelist():
            sys.stderr.write("NAME %s\n"%name) ##DWM::
        self.assertHasKeys(self.expectedZip, zip.namelist())
        self.assertHasKeys(zip.namelist(), self.expectedZip)
        ##DWM::
