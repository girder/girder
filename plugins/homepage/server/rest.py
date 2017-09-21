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
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from girder.utility.model_importer import ModelImporter

from . import constants


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', ('markdown',), self.getMarkdown)

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage properties including markdown content.')
    )
    def getMarkdown(self, params):
        folder = getOrCreateAssetsFolder()
        return {
            constants.PluginSettings.MARKDOWN: self.model('setting').get(constants.PluginSettings.MARKDOWN),
            constants.PluginSettings.HEADER: self.model('setting').get(constants.PluginSettings.HEADER),
            constants.PluginSettings.SUBHEADER: self.model('setting').get(constants.PluginSettings.SUBHEADER),
            constants.PluginSettings.WELCOME_TEXT: self.model('setting').get(constants.PluginSettings.WELCOME_TEXT),
            constants.PluginSettings.LOGO: self.model('setting').get(constants.PluginSettings.LOGO),
            'folderId': folder['_id']
        }


def getOrCreateAssetsFolder():
    collection = ModelImporter.model('collection').createCollection(
        constants.COLLECTION_NAME, public=False, reuseExisting=True)
    folder = ModelImporter.model('folder').createFolder(
        collection, constants.COLLECTION_NAME, parentType='collection', public=True, reuseExisting=True)
    return folder

