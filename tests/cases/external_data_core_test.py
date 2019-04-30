# -*- coding: utf-8 -*-
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
