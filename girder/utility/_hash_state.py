# Utility for saving and restoring the internal state of a hash object
# so that checksums can be streamed without having to remain in memory.
# Inspired by http://code.activestate.com/recipes/
# 578479-save-and-restore-sha-512-internal-state/

import binascii
import ctypes
import hashlib
import ssl
import sys

_ver = sys.version_info
_free_threaded = hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled()
_WORD = ctypes.sizeof(ctypes.c_void_p)

# This is the offset to the EVP_MD_CTX structure in CPython's _hashopenssl.c
# EVPObject.  It changed for Python 3.8 in
# https://github.com/python/cpython/pull/16023 and again for the free-threaded
# builds in 3.14 (which add two words to the object header) and for all builds
# in 3.15 (which add one word).  These values are only used as a fallback on
# platforms where we cannot safely auto-detect the layout.
if _free_threaded:
    _HASHLIB_EVP_STRUCT_OFFSET = 5 if _ver >= (3, 15) else 4
else:
    _HASHLIB_EVP_STRUCT_OFFSET = 3 if _ver >= (3, 15) else 2

# Number of pointer-sized words to scan when auto-detecting the layout of
# CPython's _hashlib.HASH object and the OpenSSL EVP_MD_CTX structure it
# references.  The digest state has never been stored inline in the hash
# object (since CPython 2.7.13), so it is always reachable via two levels of
# pointers: the hash object points to an EVP_MD_CTX, which points to the
# state data.
_HASHLIB_OBJECT_SCAN_WORDS = 10
_EVP_MD_CTX_SCAN_WORDS = 16

# Minimum plausible heap address; anything smaller is not a real pointer.
_MIN_VALID_ADDRESS = 0x1000

# Auto-detected offsets, in units of words: (offset of the EVP_MD_CTX pointer
# within the hash object, offset of the state data pointer within the
# EVP_MD_CTX).  Set once the first hash object has been inspected and reused
# for all subsequent objects, since the layout is the same for every hash
# algorithm within a single interpreter build.
_STATE_OFFSETS = None


def _readPointer(address):
    return ctypes.cast(address, ctypes.POINTER(ctypes.c_void_p))[0]


def _getReadableAddressRanges():
    """
    Get the readable memory ranges of the current process, used to validate
    candidate pointers before dereferencing them.

    :returns: A list of (start, end) address tuples, or None if the platform
        does not provide the information (in which case hardcoded offsets are
        used instead).
    """
    try:
        with open('/proc/self/maps') as mapsFile:
            ranges = []
            for line in mapsFile:
                fields = line.split()
                if 'r' not in fields[1]:
                    continue
                start, end = fields[0].split('-')
                ranges.append((int(start, 16), int(end, 16)))
            return ranges
    except (OSError, IndexError, ValueError):
        return None


def _isValidAddress(ranges, address, size):
    """
    Check that an address range is safe to read without segfaulting.
    """
    if not address or address < _MIN_VALID_ADDRESS:
        return False
    return any(start <= address and address + size <= end for start, end in ranges)


def _locateStateDataAddress(hashObject, initVectorFirstWord, stateSize):
    """
    Find the address of the internal hash state of a hash object.

    When possible, this is done by scanning the hash object for a pointer to
    an OpenSSL EVP_MD_CTX and scanning that for a pointer to memory that
    begins with the algorithm's initialization vector.  This avoids depending
    on hardcoded struct offsets, which CPython has repeatedly changed (see
    the fallback offsets below the imports).  On platforms where memory
    ranges cannot be enumerated, the hardcoded offsets are used instead.

    :param hashObject: A hashlib hash object backed by OpenSSL
        (_hashlib.HASH).
    :param initVectorFirstWord: The first eight bytes of the digest state of a
        freshly initialized hash object of this algorithm.
    :param stateSize: The size in bytes of the digest state.
    :return: The address of the digest state, or None if it could not be
        located.
    """
    global _STATE_OFFSETS
    objectAddress = id(hashObject)

    if _STATE_OFFSETS is not None:
        objectOffset, ctxOffset = _STATE_OFFSETS
        ctxAddress = _readPointer(objectAddress + objectOffset * _WORD)
        return _readPointer(ctxAddress + ctxOffset * _WORD)

    ranges = _getReadableAddressRanges()
    if ranges is None:
        # Platforms without /proc/self/maps, such as macOS and Windows.
        ctxAddress = _readPointer(objectAddress + _HASHLIB_EVP_STRUCT_OFFSET * _WORD)
        if ssl._OPENSSL_API_VERSION < (3, 0):
            # OpenSSL 1.x
            return _readPointer(ctxAddress + 3 * _WORD)
        # OpenSSL 3.x
        return _readPointer(ctxAddress + 7 * _WORD)

    for objectOffset in range(2, _HASHLIB_OBJECT_SCAN_WORDS):
        ctxAddress = _readPointer(objectAddress + objectOffset * _WORD)
        if not _isValidAddress(ranges, ctxAddress, _EVP_MD_CTX_SCAN_WORDS * _WORD):
            continue
        for ctxOffset in range(_EVP_MD_CTX_SCAN_WORDS):
            stateAddress = _readPointer(ctxAddress + ctxOffset * _WORD)
            if not _isValidAddress(ranges, stateAddress, stateSize):
                continue
            if ctypes.cast(
                stateAddress, ctypes.POINTER(ctypes.c_char)
            )[:8] == initVectorFirstWord:
                _STATE_OFFSETS = (objectOffset, ctxOffset)
                return stateAddress
    return None


def _getStateDataPointer(hashObject, hashInfo):
    """
    Get a pointer to the internal hash state of a hash object.

    :param hashObject: A hashlib hash object.
    :param hashInfo: The _HashInfo instance describing the hash algorithm.
    :return: A ctypes pointer to the internal hash state.
    :rtype: ctypes.POINTER(ctypes.c_char)
    """
    stateAddress = _locateStateDataAddress(
        hashObject, hashInfo.initVectorFirstWord, hashInfo.stateSize)
    if stateAddress is None:
        raise RuntimeError(
            'Could not locate the internal state of the %s hash object. This module '
            'requires a CPython build with OpenSSL-backed hashlib.' % hashInfo.name)
    return ctypes.cast(stateAddress, ctypes.POINTER(ctypes.c_char))


_HASH_INFOS = {}


class _HashInfo:
    def __init__(self, type, stateSize, initVectorFirstWord):
        self.type = type
        self.stateSize = stateSize
        self.initVectorFirstWord = initVectorFirstWord

        # Instantiate to get the name and do a sanity check
        instance = self.type()
        self.name = instance.name

        stateDataPointer = _getStateDataPointer(instance, self)
        assert stateDataPointer[:8] == initVectorFirstWord

        _HASH_INFOS[self.name] = self


_HashInfo(
    type=hashlib.md5,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/md5/md5.h#L100
    stateSize=92,
    # Found empirically
    initVectorFirstWord=b'\x01\x23\x45\x67\x89\xab\xcd\xef'
)
_HashInfo(
    type=hashlib.sha1,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha.h#L100
    stateSize=96,
    # Found empirically
    initVectorFirstWord=b'\x01\x23\x45\x67\x89\xab\xcd\xef'
)
_HashInfo(
    type=hashlib.sha224,
    # Uses the same struct as sha256
    stateSize=112,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha256.c#L22
    initVectorFirstWord=b'\xd8\x9e\x05\xc1\x07\xd5\x7c\x36'
)
_HashInfo(
    type=hashlib.sha256,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha.h#L135
    stateSize=112,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha256.c#L33
    initVectorFirstWord=b'\x67\xe6\x09\x6a\x85\xae\x67\xbb'
)
_HashInfo(
    type=hashlib.sha384,
    # Uses the same struct as sha512
    stateSize=216,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha512.c#L64
    initVectorFirstWord=b'\xd8\x9e\x05\xc1\x5d\x9d\xbb\xcb'
)
_HashInfo(
    type=hashlib.sha512,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha.h#L182
    stateSize=216,
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha512.c#L80
    initVectorFirstWord=b'\x08\xc9\xbc\xf3\x67\xe6\x09\x6a'
)


def serialize(hashObject):
    """
    Serializes the internal state of the hash object passed in. Calling
    restore() on the serialized value afterward will return an equivalent
    hash object to the one passed.

    :param hashObject: The hash object to serialize.
    :type hashObject: _hashlib.HASH
    :returns: A binary string representing the serialized state.
    """
    hashInfo = _HASH_INFOS[hashObject.name]
    stateDataPointer = _getStateDataPointer(hashObject, hashInfo)
    return stateDataPointer[:hashInfo.stateSize]


def restore(oldStateData, hashName):
    """
    Unserializes a hash object from a binary string created by the
    serialize() method in this module.

    :param oldStateData: The serialized state.
    :type oldStateData: binary string
    :param hashName: The name of the hash algorithm type.
    :type hashName: str
    :returns: A hash object in the same state as the one that serialize()
              was called on.
    """
    hashInfo = _HASH_INFOS[hashName]
    assert len(oldStateData) == hashInfo.stateSize

    hashObject = hashInfo.type()
    stateDataPointer = _getStateDataPointer(hashObject, hashInfo)

    for i, byte in enumerate(oldStateData):
        stateDataPointer[i] = byte

    return hashObject


def serializeHex(hashObject):
    return binascii.b2a_hex(serialize(hashObject))


def restoreHex(oldHexStateData, hashName):
    return restore(binascii.a2b_hex(oldHexStateData), hashName)
