# -*- coding: utf-8 -*-
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
