#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

_cachedDefaultImage = None


class PluginSettings(object):
    DEFAULT_IMAGE = 'gravatar.default_image'


@setting_utilities.default(PluginSettings.DEFAULT_IMAGE)
def _defaultDefaultImage():
    return 'identicon'


@setting_utilities.validator(PluginSettings.DEFAULT_IMAGE)
def _validateDefaultImage(doc):
    # TODO: this is not called when the setting is deleted
    ModelImporter.model('user').update(
        # TODO: is this faster without the query? (it's a no-op on docs without the field)
        {'gravatar_baseUrl': {'$exists': True}},
        {'$unset': {'gravatar_baseUrl': ''}},
        multi=True
    )
    # Invalidate cached default image since setting changed
    global _cachedDefaultImage
    _cachedDefaultImage = None


def getDefaultImage():
    global _cachedDefaultImage
    if _cachedDefaultImage is None:
        _cachedDefaultImage = ModelImporter.model('setting').get(PluginSettings.DEFAULT_IMAGE)
    return _cachedDefaultImage
