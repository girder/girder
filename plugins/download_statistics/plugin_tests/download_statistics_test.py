# -*- coding: utf-8 -*-
import os
import json

from tests import base
from girder.constants import ROOT_DIR
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('download_statistics')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DownloadStatisticsTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        # Create admin user
        admin = {'email': 'admin@girder.test',
                 'login': 'adminLogin',
                 'firstName': 'adminFirst',
                 'lastName': 'adminLast',
                 'password': 'adminPassword',
                 'admin': True}
        self.admin = User().createUser(**admin)

        self.filesDir = os.path.join(ROOT_DIR, 'plugins', 'download_statistics',
                                     'plugin_tests', 'files')

    def _downloadFolder(self, folderId):
        # Download folder through REST api
        path = '/folder/%s/download' % str(folderId)
        resp = self.request(path, isJson=False)
        self.assertStatusOk(resp)

        # Iterate through generator to trigger download events
        for data in resp.body:
            data

    def _downloadItem(self, itemId):
        # Download item through REST api
        path = '/item/%s/download' % str(itemId)
        resp = self.request(path, isJson=False)
        self.assertStatusOk(resp)

        # Iterate through generator to trigger download events
        for data in resp.body:
            data

    def _downloadFile(self, fileId):
        # Download file through REST api
        path = '/file/%s/download' % str(fileId)
        resp = self.request(path, isJson=False)
        self.assertStatusOk(resp)

        # Iterate through generator to trigger download events
        for data in resp.body:
            data

    def _checkDownloadsCount(self, fileId, started, requested, completed):
        # Downloads file info and asserts download statistics are accurate
        path = '/file/%s' % str(fileId)
        resp = self.request(path, isJson=True)
        self.assertStatusOk(resp)
        data = resp.json

        # The generator is never iterated as to not trigger additional events
        self.assertEqual(data['downloadStatistics']['started'], started)
        self.assertEqual(data['downloadStatistics']['requested'], requested)
        self.assertEqual(data['downloadStatistics']['completed'], completed)

    def _downloadFileInTwoChunks(self, fileId):
        # Adds 1 to downloads started, 2 to requested, and 1 to completed
        # txt1.txt and txt2.txt each have a filesize of 5
        path = '/file/%s/download' % str(fileId)
        params = {
            'offset': 0,
            'endByte': 3
        }
        resp = self.request(path, method='GET', isJson=False, params=params)
        # Iterate through generator to trigger download events
        for data in resp.body:
            data

        params['offset'] = 3
        params['endByte'] = 6
        resp = self.request(path, method='GET', isJson=False, params=params)
        # Iterate through generator to trigger download events
        for data in resp.body:
            data

    def _downloadPartialFile(self, fileId):
        # Adds 1 to downloads started and 4 to downloads requested
        # txt1.txt and txt2.txt each have a filesize of 5
        path = '/file/%s/download' % str(fileId)
        for i in range(1, 5):
            params = {
                'offset': i - 1,
                'endByte': i
            }
            resp = self.request(path, method='GET', isJson=False, params=params)
            # Iterate through generator to trigger download events
            for data in resp.body:
                data

    def testDownload(self):
        collection = Collection().createCollection('collection1', public=True)
        folder = Folder().createFolder(collection, 'folder1', parentType='collection', public=True)
        item = Item().createItem('item1', self.admin, folder)

        # Path to test files
        file1Path = os.path.join(self.filesDir, 'txt1.txt')
        file2Path = os.path.join(self.filesDir, 'txt2.txt')

        # Upload files to item
        with open(file1Path, 'rb') as fp:
            file1 = Upload().uploadFromFile(
                fp, os.path.getsize(file1Path), 'txt1.txt', parentType='item',
                parent=item, user=self.admin)

        with open(file2Path, 'rb') as fp:
            file2 = Upload().uploadFromFile(
                fp, os.path.getsize(file2Path), 'txt2.txt', mimeType='image/jpeg',
                parentType='item', parent=item, user=self.admin)

        # Download item and its files several times and ensure downloads are recorded
        # Each file is downloaded 10 times
        for _ in range(0, 5):
            self._downloadItem(item['_id'])
            self._downloadFile(file1['_id'])
            self._downloadFile(file2['_id'])

        # Download each file 1 time by downloading parent folder
        self._downloadFolder(folder['_id'])

        # Download each file over 2 requests
        self._downloadFileInTwoChunks(file1['_id'])
        self._downloadFileInTwoChunks(file2['_id'])

        # Download each file partially, adding 1 to start and 4 to requested
        self._downloadPartialFile(file1['_id'])
        self._downloadPartialFile(file2['_id'])

        # Download entire collection
        # Each file is downloaded 1 additional time
        path = '/collection/%s/download' % collection['_id']
        resp = self.request(path, user=self.admin, isJson=False)

        # Iterate through generator to trigger download events
        for data in resp.body:
            data

        # Download collection filtered by mime type
        # file2 is downloaded one additional time
        path = '/collection/%s/download' % collection['_id']
        resp = self.request(path, user=self.admin, isJson=False, method='GET',
                            params={
                                'id': collection['_id'],
                                'mimeFilter': json.dumps(['image/jpeg'])
                            })

        # iterate through generator to trigger download events
        for data in resp.body:
            data

        self._checkDownloadsCount(file1['_id'], 14, 18, 13)
        self._checkDownloadsCount(file2['_id'], 15, 19, 14)
