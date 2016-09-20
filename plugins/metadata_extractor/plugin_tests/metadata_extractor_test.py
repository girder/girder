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

import os.path
import time

from tests import base
from girder.constants import ROOT_DIR


class MetadataExtractorTestCase(base.TestCase):

    def _postUpload(self, event):
        self.processedCount += 1

    def _waitForProcessCount(self, count):
        startTime = time.time()
        while time.time()-startTime < 15:
            if self.processedCount >= count:
                break
            time.sleep(0.1)
        self.assertGreaterEqual(self.processedCount, count)

    def setUp(self):
        super(MetadataExtractorTestCase, self).setUp()

        self.processedCount = 0
        from girder import events
        events.bind('data.process', 'metadata_extractor_test',
                    self._postUpload)

        self.password = '3achAst5jaWRaCrU'
        self.user = self.model('user').createUser(
            'metadataextractor', self.password, 'Metadata', 'Extractor',
            'metadataextractor@girder.org')
        folders = self.model('folder').childFolders(self.user, 'user',
                                                    user=self.user)
        publicFolders = [folder for folder in folders if folder['public']]
        self.assertIsNotNone(publicFolders)
        self.name = 'Girder_Favicon.png'
        self.mimeType = 'image/png'
        self.item = self.model('item').createItem(self.name, self.user,
                                                  publicFolders[0])
        self.path = os.path.join(ROOT_DIR, 'clients', 'web', 'static', 'img',
                                 self.name)
        upload = self.model('upload').createUpload(
            self.user, self.name, 'item', self.item, os.path.getsize(self.path),
            self.mimeType)
        with open(self.path, 'rb') as fd:
            uploadedFile = self.model('upload').handleChunk(upload, fd)
        self.assertHasKeys(uploadedFile,
                           ['assetstoreId', 'created', 'creatorId', 'itemId',
                            'mimeType', 'name', 'size'])
        self._waitForProcessCount(1)

        self.name2 = 'small.tiff'
        self.item2 = self.model('item').createItem(self.name2, self.user,
                                                   publicFolders[0])
        self.mimeType2 = 'image/tiff'
        file2 = os.path.join(os.path.dirname(__file__), 'files', 'small.tiff')
        self.model('upload').uploadFromFile(
            open(file2), os.path.getsize(file2), self.name2, 'item',
            self.item2, self.user)
        self._waitForProcessCount(2)
