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

# Utility for saving and restoring the internal state of a sha512 object
# so that checksums can be streamed without having to remain in memory.
# Taken and adapted from http://code.activestate.com/recipes/
# 578479-save-and-restore-sha-512-internal-state/

from hashlib import sha512
import ctypes
import binascii

POFFSET = 6
STATESIZE = 216


def serialize(sha512Object):
    """
    Serializes the internal state of the sha512 object passed in. Calling
    restore() on the serialized value afterward will return an equivalent
    sha512 object to the one passed.
    :param sha512Object: The sha512 object to serialize.
    :type sha512Object: sha512
    :returns: A binary string representing the serialized state.
    """
    datap = ctypes.cast(
        ctypes.cast(id(sha512Object), ctypes.POINTER(ctypes.c_voidp))[POFFSET],
        ctypes.POINTER(ctypes.c_char))
    assert datap

    return datap[:STATESIZE]


def restore(data):
    """
    Unserializes a sha512 object from a binary string created by the
    serialize() method in this module.
    :param data: The serialized state.
    :type data: binary string
    :returns: A sha512 object in the same state as the one that serialize()
              was called on.
    """
    checksum = sha512()
    datap = ctypes.cast(
        ctypes.cast(id(checksum), ctypes.POINTER(ctypes.c_voidp))[POFFSET],
        ctypes.POINTER(ctypes.c_char))
    assert datap
    assert datap[:8] == '\x08\xc9\xbc\xf3g\xe6\tj'  # first sha512 word

    for i, byte in enumerate(data):
        assert i < STATESIZE
        datap[i] = byte
    assert i + 1 == STATESIZE

    return checksum


def serializeHex(o):
    return binascii.b2a_hex(serialize(o))


def restoreHex(d):
    return restore(binascii.a2b_hex(d))
