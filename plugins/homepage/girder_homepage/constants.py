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

import six

from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.file import File
from girder.utility import setting_utilities


COLLECTION_NAME = 'Homepage Assets'


class PluginSettings(object):
    MARKDOWN = 'homepage.markdown'

    HEADER = 'homepage.header'
    SUBHEADER = 'homepage.subheader'

    WELCOME_TEXT = 'homepage.welcome_text'

    LOGO = 'homepage.logo'


@setting_utilities.default(PluginSettings.MARKDOWN)
def _defaultMarkdown():
    return ''


@setting_utilities.default(PluginSettings.HEADER)
def _defaultHeader():
    return 'Girder'


@setting_utilities.default(PluginSettings.SUBHEADER)
def _defaultSubheader():
    return 'Data management platform'


@setting_utilities.default(PluginSettings.WELCOME_TEXT)
def _defaultWelcomeText():
    return 'Welcome to Girder!'


@setting_utilities.default(PluginSettings.LOGO)
def _defaultLogo():
    return None


@setting_utilities.validator({
    PluginSettings.MARKDOWN,
    PluginSettings.HEADER,
    PluginSettings.SUBHEADER,
    PluginSettings.WELCOME_TEXT
})
def _validateStrings(doc):
    if not isinstance(doc['value'], six.string_types):
        raise ValidationException('The setting is not a string', 'value')


@setting_utilities.validator(PluginSettings.LOGO)
def _validateLogo(doc):
    try:
        logoFile = File().load(doc['value'], level=AccessType.READ, user=None, exc=True)
    except ValidationException as e:
        # Invalid ObjectId, or non-existent document
        raise ValidationException(e.message, 'value')
    except AccessException:
        raise ValidationException('Logo must be publicly readable', 'value')

    # Store this field natively as an ObjectId
    doc['value'] = logoFile['_id']
