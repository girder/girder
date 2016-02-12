#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

from .. import base
from girder.utility import hash_state
import hashlib
import sys


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class HashStateTestCase(base.TestCase):

    def setUp(self):
        # Define a few variables used by all the tests:
        # Use the python's zen as 'long' string
        import this
        testChunk = this.s.encode('utf8')
        # Arbitrary number to split the python zen in a least a few chunks
        chunkSize = len(testChunk) // 6
        self.chunks = [
            testChunk[i:i+chunkSize]
            for i in range(0, len(testChunk), chunkSize)
            ]

    def tearDown(self):
        base.stopServer()

    def _simpleHashingTest(self, hash_type):
        """
        Test the hashing of hash_state against Python's hashlib

        :param hash_type: String representing the hash algorithm to use
        """
        officialHasher = hashlib.new(hash_type)
        state = hash_state.serializeHex(hashlib.new(hash_type))

        for chunk in self.chunks:
            checksum = hash_state.restoreHex(state, hash_type)
            self.assertEquals(officialHasher.hexdigest(), checksum.hexdigest())
            self.assertEquals(officialHasher.digest(), checksum.digest())

            officialHasher.update(chunk)
            checksum.update(chunk)
            state = hash_state.serializeHex(checksum)

        checksum = hash_state.restoreHex(state, hash_type)
        self.assertEquals(officialHasher.hexdigest(), checksum.hexdigest())
        self.assertEquals(officialHasher.digest(), checksum.digest())

    def testSimpleHashing(self):
        """
        Test all the base algorithms against Python's hashlib
        """
        if sys.version_info <= (3, 2):
            algorithms = hashlib.algorithms
        else:
            algorithms = hashlib.algorithms_guaranteed

        for algo in algorithms:
            self._simpleHashingTest(algo)
