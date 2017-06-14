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

        folders = self.model('folder').childFolders(parent=self.admin, parentType='user',
                                                    user=self.admin)

        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder

        self.filesDir = os.path.join(ROOT_DIR, 'plugins', 'download_statistics',
                                     'plugin_tests', 'files')

    def _downloadItem(self, itemId):
        # Download item through REST api
        path = '/item/%s/download' % str(itemId)
        resp = self.request(path, user=self.admin, isJson=False)
        self.assertStatusOk(resp)

    def _downloadFile(self, fileId):
        # Download file through REST api
        path = '/file/%s/download' % str(fileId)
        resp = self.request(path, user=self.admin, isJson=False)
        self.assertStatusOk(resp)

    def _checkDownloadsStarted(self, fileId, count):
        # Test downloadsStarted is equal to count
        file = self.model('file').load(fileId, force=True)
        self.assertEqual(file['downloadsStarted'], count, 'downloadsStarted count inaccurate')

    def testFileDownload(self):
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
            self.model('upload').uploadFromFile(fp, os.path.getsize(file2Path),
                                                'txt2.txt', parentType='item',
                                                parent=item, user=self.admin)

        # Download item, and its files, several times and ensure downloads are recorded
        for n in range(0, 5):
            self._downloadItem(item['_id'])
        files = list(self.model('item').childFiles(item=item))
        self.assertTrue(files)
        for file in files:
            self._checkDownloadsStarted(file['_id'], 5)
