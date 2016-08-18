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
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

KEY = 'homepage.markdown'
NAME = 'Homepage Assets'


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', ('markdown',), self.getMarkdown)

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage markdown.')
    )
    def getMarkdown(self, params):
        folder = getOrCreateAssetsFolder()
        return {
            KEY: self.model('setting').get(KEY),
            'folderId': folder['_id']
        }


@setting_utilities.validator(KEY)
def validateHomepageMarkdown(event):
    pass


def getOrCreateAssetsFolder():
    collection = ModelImporter.model('collection').createCollection(
        NAME, public=False, reuseExisting=True)
    folder = ModelImporter.model('folder').createFolder(
        collection, NAME, parentType='collection', public=True, reuseExisting=True)
    return folder


def load(info):
    info['apiRoot'].homepage = Homepage()
