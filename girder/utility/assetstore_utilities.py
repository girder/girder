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

assetstoreAdapter = None
currentAssetstore = None


def getAssetstoreAdapter(refresh=False):
    """
    This is a factory method that will return the appropriate assetstore adapter
    based on the server's configuration. The returned object will conform to
    the interface of the AbstractAssetstoreAdapter.
    :param refresh: Set this to True to force a reinitialization.
    :type refresh: bool
    """
    global assetstoreAdapter
    if assetstoreAdapter is None or refresh:
        assetstore = getCurrentAssetstore()
        if assetstore['type'] == AssetstoreType.FILESYSTEM:
            assetstoreAdapter = FilesystemAssetstoreAdapter(assetstore['root'])
        elif assetstore['type'] == AssetstoreType.GRIDFS:
            raise Exception('GridFS assetstore adapter not implemented.')
        elif assetstore['type'] == AssetstoreType.S3:
            raise Exception('S3 assetstore adapter not implemented.')

    return assetstoreAdapter


def getCurrentAssetstore(refresh=False):
    """
    Returns the singleton assetstore document representing the current
    assetstore, i.e. the assetstore that uploads will be placed into.
    :param refresh: Set this to True to force a reinitialization.
    :type refresh: bool
    """
    global currentAssetstore
    if currentAssetstore is None or refresh:
        assetstoreModel = ModelImporter().model('assetstore')
        currentAssetstore = assetstoreModel.getCurrent()

    return currentAssetstore
