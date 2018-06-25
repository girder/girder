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

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting

from . import constants


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', (), self.getSettings)
        self.route('GET', ('assets',), self.getAssets)

    @access.public
    @autoDescribeRoute(
        Description('Public url for getting the homepage properties.')
    )
    def getSettings(self):
        settings = Setting()
        return {
            constants.PluginSettings.MARKDOWN: settings.get(constants.PluginSettings.MARKDOWN),
            constants.PluginSettings.HEADER: settings.get(constants.PluginSettings.HEADER),
            constants.PluginSettings.SUBHEADER: settings.get(constants.PluginSettings.SUBHEADER),
            constants.PluginSettings.WELCOME_TEXT: settings.get(
                constants.PluginSettings.WELCOME_TEXT),
            constants.PluginSettings.LOGO: settings.get(constants.PluginSettings.LOGO),
        }

    @access.admin
    @autoDescribeRoute(
        Description('Return the folder IDs for uploaded asset content.')
    )
    def getAssets(self):
        return {
            # Keep MARKDOWN folder as 'Homepage Assets', for compatibility
            constants.PluginSettings.MARKDOWN: self._getAssetsFolder('Homepage Assets')['_id'],
            constants.PluginSettings.WELCOME_TEXT: self._getAssetsFolder('Welcome Text')['_id'],
            constants.PluginSettings.LOGO: self._getAssetsFolder('Logo')['_id'],
        }

    def _getAssetsFolder(self, folderName):
        """
        Get or create a public folder, in the private "Homepage Assets" collection.

        This makes the folder effectively "unlisted" as it can't be browsed to by normal users, but
        its content can still be downloaded directly.

        :param folderName: The name of the folder to get or create.
        :return: The new folder document.
        """
        collection = Collection().createCollection(
            constants.COLLECTION_NAME,
            public=False,
            reuseExisting=True
        )
        folder = Folder().createFolder(
            collection,
            folderName,
            parentType='collection',
            public=True,
            reuseExisting=True
        )
        return folder
