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

import unittest
import hashlib
import os


class ExternalDataCoreTest(unittest.TestCase):
    def testExternalDataFile(self):
        """Asserts that the external data file was correctly downloaded."""
        filepath = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'],
            'test_file.txt'
        )
        self.assertTrue(
            os.path.exists(filepath),
            'The test file does not exist.'
        )

        hash = hashlib.md5()
        with open(filepath, 'r') as f:
            hash.update(f.read().encode('utf-8'))
            self.assertEqual(
                hash.hexdigest(),
                '169293f7c9138e4b50ebcab4358dc509',
                'Invalid test file content.'
            )
