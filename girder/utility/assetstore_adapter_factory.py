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

from .filesystem_assetstore_adapter import FilesystemAssetstoreAdapter
from girder.constants import ROOT_DIR

assetstoreAdapter = None
currentAssetstore = None


def getAssetstoreAdapter():
    """
    This is a factory method that will return the appropriate assetstore adapter
    based on the server's configuration. The returned object will conform to
    the interface of the AbstractAssetstoreAdapter.
    """
    global assetstoreAdapter
    if assetstoreAdapter is None:
        # TODO base the assetstore adapter singleton on the server config
        assetstoreAdapter = FilesystemAssetstoreAdapter(ROOT_DIR)

    return assetstoreAdapter


def getCurrentAssetstore():
    """
    Returns the singleton assetstore document representing the current
    assetstore, i.e. the assetstore that uploads will be placed into.
    """
    global currentAssetstore
    if currentAssetstore is None:
        currentAssetstore = 1  # TODO set this to current assetstore

    return currentAssetstore
