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
import this

testData = this.s.encode('utf8')
chunkSize = len(testData) // 6
chunks = [testData[i:i + chunkSize] for i in range(0, len(testData), chunkSize)]


@pytest.mark.parametrize('alg', [
    hashlib.md5,
    hashlib.sha1,
    hashlib.sha224,
    hashlib.sha256,
    hashlib.sha384,
    hashlib.sha512
])
def testSimpleHashing(algorithm):
    canonicalHash = algorithm()
    runningState = hash_state.serializeHex(algorithm())
    hashName = canonicalHash.name

    for chunk in chunks:
        runningHash = hash_state.restoreHex(runningState, hashName)
        assert canonicalHash.hexdigest() == runningHash.hexdigest()
        assert canonicalHash.digest() == runningHash.digest()

        canonicalHash.update(chunk)
        runningHash.update(chunk)
        runningState = hash_state.serializeHex(runningHash)

    runningHash = hash_state.restoreHex(runningState, hashName)
    assert canonicalHash.hexdigest() == runningHash.hexdigest()
    assert canonicalHash.digest() == runningHash.digest()
