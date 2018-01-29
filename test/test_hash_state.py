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


@pytest.fixture
def iterableBytes():
    chunkSize = 256
    chunkCount = 6
    # A one-time iterable, with elements:
    #  b'0000...'
    #  b'1111...'
    #  ...
    iterable = (
        str(chunkNum).encode('utf8') * chunkSize
        for chunkNum in range(chunkCount)
    )

    yield iterable


@pytest.mark.parametrize('algorithmName', [
    'md5',
    'sha1',
    'sha224',
    'sha256',
    'sha384',
    'sha512'
])
def testSimpleHashing(iterableBytes, algorithmName):
    canonicalHash = hashlib.new(algorithmName)
    runningHash = hashlib.new(algorithmName)
    runningState = hash_state.serializeHex(runningHash)

    for chunk in iterableBytes:
        runningHash = hash_state.restoreHex(runningState, algorithmName)
        assert canonicalHash.hexdigest() == runningHash.hexdigest()
        assert canonicalHash.digest() == runningHash.digest()

        canonicalHash.update(chunk)
        runningHash.update(chunk)
        runningState = hash_state.serializeHex(runningHash)

    runningHash = hash_state.restoreHex(runningState, algorithmName)
    assert canonicalHash.hexdigest() == runningHash.hexdigest()
    assert canonicalHash.digest() == runningHash.digest()
