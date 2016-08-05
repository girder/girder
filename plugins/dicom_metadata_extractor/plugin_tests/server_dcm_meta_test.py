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

from tests import base
from . dicom_metadata_extractor_test import DicomMetadataExtractorTestCase


def setUpModule():
    base.enabledPlugins.append('dicom_metadata_extractor')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ServerDicomMetadataExtractorTestCase(DicomMetadataExtractorTestCase):
    def testServerDicomMetadataExtractor(self):
        startTime = time.time()
        while True:
            item = self.model('item').load(self.item['_id'], user=self.user)
            if 'meta' in item:
                if 'Patient ID' in item['meta']:
                    break
            if time.time()-startTime > 15:
                break
            time.sleep(0.1)
        self.assertEqual(item['name'], self.name)
        self.assertHasKeys(item, ['meta'])
        self.assertEqual(item['meta']['Patient ID'], self.patientId)
