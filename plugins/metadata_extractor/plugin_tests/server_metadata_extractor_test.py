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

import time

from girder.models.item import Item
from tests import base
from . metadata_extractor_test import MetadataExtractorTestCase


def setUpModule():
    base.enabledPlugins.append('metadata_extractor')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ServerMetadataExtractorTestCase(MetadataExtractorTestCase):
    def testServerMetadataExtractor(self):
        startTime = time.time()
        while True:
            item = Item().load(self.item['_id'], user=self.user)
            if 'meta' in item:
                if 'MIME type' in item['meta']:
                    break
            if time.time()-startTime > 15:
                break
            time.sleep(0.1)
        self.assertEqual(item['name'], self.name)
        self.assertHasKeys(item, ['meta'])
        self.assertEqual(item['meta']['MIME type'], self.mimeType)
