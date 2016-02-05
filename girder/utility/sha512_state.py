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

from . import hash_state


def serialize(sha512Object):
    """
    .. deprecated:: 1.5
    Use :py:func:`girder.utility.hash_state.serialize`.
    """
    return hash_state.serialize(sha512Object)


def restore(data):
    """
    .. deprecated:: 1.5
    Use :py:func:`girder.utility.hash_state.restore`.
    """
    return hash_state.restore(data, 'sha512')


def serializeHex(o):
    """
    .. deprecated:: 1.5
    Use :py:func:`girder.utility.hash_state.serializeHex`.
    """
    return hash_state.serializeHex(o)


def restoreHex(d):
    """
    .. deprecated:: 1.5
    Use :py:func:`girder.utility.hash_state.restoreHex`.
    """
    return hash_state.restoreHex(d, 'sha512')
