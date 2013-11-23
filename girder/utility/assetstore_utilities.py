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

import os

from .filesystem_assetstore_adapter import FilesystemAssetstoreAdapter
from .model_importer import ModelImporter
from girder.constants import AssetstoreType


def getAssetstoreAdapter(assetstore):
    """
    This is a factory method that will return the appropriate assetstore adapter
    for the specified assetstore. The returned object will conform to
    the interface of the AbstractAssetstoreAdapter.
    :param assetstore: The assetstore document used to instantiate the adapter.
    :type assetstore: dict
    :returns: An adapter descending from AbstractAssetstoreAdapter
    """
    if assetstore['type'] == AssetstoreType.FILESYSTEM:
        assetstoreAdapter = FilesystemAssetstoreAdapter(assetstore)
    elif assetstore['type'] == AssetstoreType.GRIDFS:
        raise Exception('GridFS assetstore adapter not implemented.')
    elif assetstore['type'] == AssetstoreType.S3:
        raise Exception('S3 assetstore adapter not implemented.')

    return assetstoreAdapter


def fileIndexFields():
    """
    This will return a set of all required index fields from all of the
    different assetstore types.
    """
    return list(set(FilesystemAssetstoreAdapter.fileIndexFields()))
    # + GridFSAssetstoreAdapter.fileIndexFields()
    # + S3AssetstoreAdapter.fileIndexFields()
