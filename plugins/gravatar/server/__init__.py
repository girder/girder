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

import cherrypy
import hashlib

from girder import events
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import loadmodel
from girder.models.model_base import AccessType
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter


_cachedDefaultImage = None


class PluginSettings(object):
    DEFAULT_IMAGE = 'gravatar.default_image'


def computeBaseUrl(user):
    """
    Compute the base gravatar URL for a user and return it. For the moment, the
    current default image is cached in this URL. It is the caller's
    responsibility to save this value on the user document.
    """
    global _cachedDefaultImage
    if _cachedDefaultImage is None:
        _cachedDefaultImage = ModelImporter.model('setting').get(
            PluginSettings.DEFAULT_IMAGE, default='identicon')

    md5 = hashlib.md5(user['email'].encode('utf8')).hexdigest()
    return 'https://www.gravatar.com/avatar/%s?d=%s' % (
        md5, _cachedDefaultImage)


@access.public
@loadmodel(model='user', level=AccessType.READ)
@describeRoute(
    Description('Redirects to the gravatar image for a user.')
    .param('id', 'The ID of the user.', paramType='path')
    .param('size', 'Size in pixels for the image (default=64).', required=False,
           dataType='int')
)
def getGravatar(user, params):
    size = int(params.get('size', 64))

    if not user.get('gravatar_baseUrl'):
        # the save hook will cause the gravatar base URL to be computed
        user = ModelImporter.model('user').save(user)

    raise cherrypy.HTTPRedirect(user['gravatar_baseUrl'] + '&s=%d' % size)


@setting_utilities.validator(PluginSettings.DEFAULT_IMAGE)
def _validateDefaultImage(doc):
    # TODO should we update user collection to remove gravatar_baseUrl vals?
    # Invalidate cached default image since setting changed
    global _cachedDefaultImage
    _cachedDefaultImage = None


def _userUpdate(event):
    """
    Called when the user document is being changed. We update the cached
    gravatar URL.
    """
    event.info['gravatar_baseUrl'] = computeBaseUrl(event.info)


def load(info):
    info['apiRoot'].user.route('GET', (':id', 'gravatar'), getGravatar)

    ModelImporter.model('user').exposeFields(
        level=AccessType.READ, fields='gravatar_baseUrl')

    events.bind('model.user.save', 'gravatar', _userUpdate)
