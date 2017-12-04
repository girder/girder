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

from .external_data_core_test import ExternalDataCoreTest
import os
import hashlib


class ExternalDataPluginTest(ExternalDataCoreTest):
    def testPluginDataFile(self):
        """Asserts that the plugin data file was correctly downloaded."""
        filepath = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'],
            'plugins',
            'has_external_data',
            'plugin_test_file.txt'
        )
        self.assertTrue(
            os.path.exists(filepath),
            'The plugin file does not exist.'
        )

        hash = hashlib.md5()
        with open(filepath, 'r') as f:
            hash.update(f.read().encode('utf-8'))
            self.assertEqual(
                hash.hexdigest(),
                '41b5b2ede7a20b5f1c466db54615132e',
                'Invalid content in plugin file.'
            )
