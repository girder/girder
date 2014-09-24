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
import sys
import time

from girder.constants import ROOT_DIR
from server.metadata_extractor import ClientMetadataExtractor
from tests import base
from . metadata_extractor_test import MetadataExtractorTestCase


def setUpModule():
    os.environ['PORT'] = '50001'
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class ClientMetadataExtractorTestCase(MetadataExtractorTestCase):
    def testClientMetadataExtractor(self):
        time.sleep(0.2)
        item = self.model('item').load(self.item['_id'], user=self.user)
        self.assertEqual(item['name'], self.name)
        self.assertNotHasKeys(item, ['meta'])

        clientPath = os.path.join(ROOT_DIR, 'clients', 'python')
        sys.path.insert(0, clientPath)

        from GirderClient import GirderClient

        client = GirderClient('localhost', 50001)
        client.authenticate(self.user['login'], self.password)
        extractor = ClientMetadataExtractor(client, self.path, self.item['_id'])
        extractor.extractMetadata()
        sys.path.remove(clientPath)

        start = time.time()
        while True:
            if time.time() - start > 15:
                break

            item = self.model('item').load(self.item['_id'], user=self.user)
            if 'meta' in item and item['meta']['MIME type'] == self.mimeType:
                break

            time.sleep(0.2)

        self.assertEqual(item['name'], self.name)
        self.assertHasKeys(item, ['meta'])
        self.assertEqual(item['meta']['MIME type'], self.mimeType)
