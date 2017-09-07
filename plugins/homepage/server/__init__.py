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
SUBHEADER = 'homepage.subheader'
WELCOME_TEXT = 'homepage.welcome_text'
LOGO = 'homepage.logo'

NAME = 'Homepage Assets'


class Homepage(Resource):
    def __init__(self):
        super(Homepage, self).__init__()
        self.resourceName = 'homepage'
        self.route('GET', ('markdown',), self.getMarkdown)

    @access.public
    @describeRoute(
        Description('Public url for getting the homepage markdown and settings.')
    )
    def getMarkdown(self, params):
        folder = getOrCreateAssetsFolder()
        return {
            MARKDOWN: self.model('setting').get(MARKDOWN),
            HEADER: self.model('setting').get(HEADER),
            SUBHEADER: self.model('setting').get(SUBHEADER),
            WELCOME_TEXT: self.model('setting').get(WELCOME_TEXT),
            LOGO: self.model('setting').get(LOGO),
            'folderId': folder['_id']
        }


@setting_utilities.validator(MARKDOWN)
def validateHomepageMarkdown(event):
    pass


@setting_utilities.validator(HEADER)
def validateHomepageTitle(event):
    pass


@setting_utilities.validator(SUBHEADER)
def validateHomepageSubHeadingText(event):
    pass


@setting_utilities.validator(WELCOME_TEXT)
def validateHomepageWelcomeText(event):
    pass

@setting_utilities.validator(LOGO)
def validateHomepageLogo(event):
    pass


def getOrCreateAssetsFolder():
    collection = ModelImporter.model('collection').createCollection(
        NAME, public=False, reuseExisting=True)
    folder = ModelImporter.model('folder').createFolder(
        collection, NAME, parentType='collection', public=True, reuseExisting=True)
    return folder


def load(info):
    info['apiRoot'].homepage = Homepage()
