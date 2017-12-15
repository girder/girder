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

from girder.utility import hash_state
import hashlib
import pytest
import sys
import this

testData = this.s.encode('utf8')
chunkSize = len(testData) // 6
chunks = [testData[i:i + chunkSize] for i in range(0, len(testData), chunkSize)]
algorithms = hashlib.algorithms if sys.version_info <= (3, 2) else hashlib.algorithms_guaranteed


@pytest.mark.parametrize('alg', algorithms)
def testSimpleHashing(alg):
    canonical = hashlib.new(alg)
    state = hash_state.serializeHex(hashlib.new(alg))

    for chunk in chunks:
        checksum = hash_state.restoreHex(state, alg)
        assert canonical.hexdigest() == checksum.hexdigest()
        assert canonical.digest() == checksum.digest()

        canonical.update(chunk)
        checksum.update(chunk)
        state = hash_state.serializeHex(checksum)

    checksum = hash_state.restoreHex(state, alg)
    assert canonical.hexdigest() == checksum.hexdigest()
    assert canonical.digest() == checksum.digest()
