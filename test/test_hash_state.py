# -*- coding: utf-8 -*-
from girder.utility import _hash_state
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
    runningState = _hash_state.serializeHex(runningHash)

    for chunk in iterableBytes:
        runningHash = _hash_state.restoreHex(runningState, algorithmName)
        assert canonicalHash.hexdigest() == runningHash.hexdigest()
        assert canonicalHash.digest() == runningHash.digest()

        canonicalHash.update(chunk)
        runningHash.update(chunk)
        runningState = _hash_state.serializeHex(runningHash)

    runningHash = _hash_state.restoreHex(runningState, algorithmName)
    assert canonicalHash.hexdigest() == runningHash.hexdigest()
    assert canonicalHash.digest() == runningHash.digest()
