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


import os
import json

from tests import base
from girder.constants import ROOT_DIR


def setUpModule():
    base.enabledPlugins.append('download_statistics')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DownloadStatisticsTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        # Create admin user
        admin = {'email': 'admin@email.com',
                 'login': 'adminLogin',
                 'firstName': 'adminFirst',
                 'lastName': 'adminLast',
                 'password': 'adminPassword',
                 'admin': True}
        self.admin = self.model('user').createUser(**admin)

        self.publicFolder = self.model('folder').findOne({
            'name': 'Public',
            'parentId': self.admin['_id'],
            'parentCollection': 'user'
        })
        self.filesDir = os.path.join(ROOT_DIR, 'plugins', 'download_statistics',
                                     'plugin_tests', 'files')

    def _downloadItem(self, itemId):
        # Download item through REST api
        path = '/item/%s/download' % str(itemId)
        resp = self.request(path, user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        # iterate through generator to trigger download events
        for data in resp.body:
            data

    def _downloadFile(self, fileId):
        # Download file through REST api
        path = '/file/%s/download' % str(fileId)
        resp = self.request(path, user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        # iterate through generator to trigger download events
        for data in resp.body:
            data

    def _checkDownloadsStarted(self, fileId, count):
        # Test downloadsStarted is equal to count
        file = self.model('file').load(fileId, force=True)
        self.assertEqual(file['downloadStatistics']['started'], count,
                         'Started Downloads count inaccurate')

    def _checkDownloadsRequested(self, fileId, count):
        # Test downloadsRequested is equal to count
        file = self.model('file').load(fileId, force=True)
        self.assertEqual(file['downloadStatistics']['requested'], count,
                         'Requested Downloads count inaccurate')

    def _checkDownloadsCompleted(self, fileId, count):
        # Test downloadsCompleted is equal to count
        file = self.model('file').load(fileId, force=True)
        self.assertEqual(file['downloadStatistics']['completed'], count,
                         'Completed downloads count inaccurate')

    def _checkDownloadStatisticFields(self, fileId):
        path = '/file/' + str(fileId)
        resp = self.request(path, user=self.admin, isJson=True)
        self.assertStatusOk(resp)
        data = resp.json
        self.assertTrue(data['downloadStatistics'])
        self.assertTrue(data['downloadStatistics']['completed'])
        self.assertTrue(data['downloadStatistics']['requested'])
        self.assertTrue(data['downloadStatistics']['started'])

    def testItemAndFileDownload(self):
        # Create item
        item = self.model('item').createItem('item1', self.admin, self.publicFolder)

        # Path to test files
        file1Path = os.path.join(self.filesDir, 'txt1.txt')
        file2Path = os.path.join(self.filesDir, 'txt2.txt')

        # Upload files to item
        with open(file1Path, 'rb') as fp:
            self.model('upload').uploadFromFile(fp, os.path.getsize(file1Path),
                                                'txt1.txt', parentType='item',
                                                parent=item, user=self.admin)

        with open(file2Path, 'rb') as fp:
            self.model('upload').uploadFromFile(fp, os.path.getsize(file2Path),
                                                'txt2.txt', parentType='item',
                                                parent=item, user=self.admin)

        # Download item, and its files, several times and ensure downloads are recorded
        files = list(self.model('item').childFiles(item=item))
        self.assertTrue(files)
        for n in range(0, 5):
            self._downloadItem(item['_id'])
            for file in files:
                self._downloadFile(file['_id'])
        for file in files:
            self._checkDownloadsStarted(file['_id'], 10)
            self._checkDownloadsRequested(file['_id'], 10)
            self._checkDownloadsCompleted(file['_id'], 10)
            self._checkDownloadStatisticFields(file['_id'])

    def testCollectionDownload(self):
        # Create collection
        collection = self.model('collection').createCollection('collection1', public=True)
        # Create folder in collection
        folder = self.model('folder').createFolder(collection, 'folder1',
                                                   parentType='collection',
                                                   public=True, )
        # Create item in folder
        item = self.model('item').createItem('item1', self.admin, folder)

        # Path to test files
        file1Path = os.path.join(self.filesDir, 'txt1.txt')
        file2Path = os.path.join(self.filesDir, 'txt2.txt')

        file1 = ''
        file2 = ''

        # Upload files to item
        with open(file1Path, 'rb') as fp:
            file1 = self.model('upload').uploadFromFile(fp, os.path.getsize(file1Path),
                                                        'txt1.txt', parentType='item',
                                                        parent=item, user=self.admin)

        with open(file2Path, 'rb') as fp:
            file2 = self.model('upload').uploadFromFile(fp, os.path.getsize(file2Path),
                                                        'txt2.txt', mimeType='image/jpeg',
                                                        parentType='item', parent=item,
                                                        user=self.admin)

        # Download entire collection
        path = '/collection/%s/download' % collection['_id']
        resp = self.request(path, user=self.admin, isJson=False)

        # iterate through generator to trigger download events
        for data in resp.body:
            data

        # Download collection filtered by mime type
        path = '/collection/%s/download' % collection['_id']
        resp = self.request(path, user=self.admin, isJson=False, method='GET',
                            params={
                                'id': collection['_id'],
                                'mimeFilter': json.dumps(['image/jpeg'])
                            })

        # iterate through generator to trigger download events
        for data in resp.body:
            data

        self._checkDownloadsStarted(file1['_id'], 1)
        self._checkDownloadsRequested(file1['_id'], 1)
        self._checkDownloadsCompleted(file1['_id'], 1)

        # File 2 should have been downloaded twice since it is the required mime type
        self._checkDownloadsStarted(file2['_id'], 2)
        self._checkDownloadsRequested(file2['_id'], 2)
        self._checkDownloadsCompleted(file2['_id'], 2)
