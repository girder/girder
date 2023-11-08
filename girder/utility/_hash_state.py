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
# This is the offset to the EVP_MD_CTX structure in CPython's _hashopenssl.c
# EVPObject.  It changed for Python 3.8 in
# https://github.com/python/cpython/pull/16023
_HASHLIB_EVP_STRUCT_OFFSET = 2


def _getHashStateDataPointer(hashObject):
    """
    Get a pointer to the internal hash state of a hash object.

    :param hashObject: A hashlib hash object.
    :return: A ctypes pointer to the internal hash state.
    :rtype: ctypes.POINTER(ctypes.c_char)
    """
    hashPointer = ctypes.cast(id(hashObject), ctypes.POINTER(ctypes.c_void_p))

    # In cpython 2.7.13, hashlib changed to store a pointer to the OpenSSL hash
    # object rather than inlining it in the struct, so we require an extra dereference. See
    # https://github.com/python/cpython/commit/9d9615f6782be4b1f38b47d4d56cee208c26a970
    evpStruct = ctypes.cast(hashPointer[_HASHLIB_EVP_STRUCT_OFFSET],
                            ctypes.POINTER(ctypes.c_void_p))
    if ssl._OPENSSL_API_VERSION < (3, 0):
        # OpenSSL 1.x
        stateDataPointer = ctypes.cast(evpStruct[3], ctypes.POINTER(ctypes.c_char))
    else:
        # OpenSSL 3.x
        stateDataPointer = ctypes.cast(evpStruct[7], ctypes.POINTER(ctypes.c_char))

    assert stateDataPointer
    return stateDataPointer


_HASH_INFOS = {}


class _HashInfo:
    def __init__(self, type, stateSize, initVectorFirstWord):
        self.type = type
        self.stateSize = stateSize

        # Instantiate to get the name and do a sanity check
        instance = self.type()
        self.name = instance.name

        stateDataPointer = _getHashStateDataPointer(instance)
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
    # github.com/openssl/openssl/blob/OpenSSL_1_0_1f/crypto/sha/sha256.c#L22
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
    stateDataPointer = _getHashStateDataPointer(hashObject)
    hashInfo = _HASH_INFOS[hashObject.name]
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
    stateDataPointer = _getHashStateDataPointer(hashObject)

    for i, byte in enumerate(oldStateData):
        stateDataPointer[i] = byte

    return hashObject


def serializeHex(hashObject):
    return binascii.b2a_hex(serialize(hashObject))


def restoreHex(oldHexStateData, hashName):
    return restore(binascii.a2b_hex(oldHexStateData), hashName)
