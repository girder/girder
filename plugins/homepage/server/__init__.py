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

MARKDOWN = 'homepage.markdown'
HEADER = 'homepage.header'
SUBHEADING_TEXT = 'homepage.subheading_text'
WELCOME_TEXT = 'homepage.welcome_text'

NAME = 'Homepage Assets'


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', ('markdown',), self.getMarkdown)
        self.route('GET', ('settings',), self.getSettingFrontPage)

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage markdown.')
    )
    def getMarkdown(self, params):
        folder = getOrCreateAssetsFolder()
        return {
            MARKDOWN: self.model('setting').get(MARKDOWN),
            'folderId': folder['_id']
        }

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage settings.')
    )
    def getSettingFrontPage(self, params):
        folder = getOrCreateAssetsFolder()
        return {
            HEADER: self.model('setting').get(HEADER),
            SUBHEADING_TEXT: self.model('setting').get(SUBHEADING_TEXT),
            WELCOME_TEXT: self.model('setting').get(WELCOME_TEXT),
            'folderId': folder['_id']
        }

@setting_utilities.validator(MARKDOWN)
def validateHomepageMarkdown(event):
    pass
@setting_utilities.validator(HEADER)
def validateHomepageTitle(event):
    pass
@setting_utilities.validator(SUBHEADING_TEXT)
def validateHomepageTitle(event):
    pass
@setting_utilities.validator(WELCOME_TEXT)
def validateHomepageTitle(event):
    pass

def getOrCreateAssetsFolder():
    collection = ModelImporter.model('collection').createCollection(
        NAME, public=False, reuseExisting=True)
    folder = ModelImporter.model('folder').createFolder(
        collection, NAME, parentType='collection', public=True, reuseExisting=True)
    return folder


def load(info):
    info['apiRoot'].homepage = Homepage()

# DEBUG
def function ():
    home = Homepage()
    folder = getOrCreateAssetsFolder()
    return  {
                HEADER: home.model('setting').get(HEADER),
                SUBHEADING_TEXT: home.model('setting').get(SUBHEADING_TEXT),
                WELCOME_TEXT: home.model('setting').get(WELCOME_TEXT),
                'folderId': folder['_id']
            }
