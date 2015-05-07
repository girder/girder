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
from girder.api.describe import Description
from girder.api.rest import loadmodel
from girder.models.model_base import AccessType
from girder.utility.model_importer import ModelImporter


_cachedDefaultImage = None


class PluginSettings(object):
    DEFAULT_IMAGE = 'gravatar.default_image'


def computeBaseUrl(user):
    """
    Compute the base gravatar URL for a user and save the value in the user
    document. For the moment, the current default image is cached in this URL.
    """
    global _cachedDefaultImage
    if _cachedDefaultImage is None:
        _cachedDefaultImage = ModelImporter.model('setting').get(
            PluginSettings.DEFAULT_IMAGE, default='identicon')

    md5 = hashlib.md5(user['email'].encode('utf8')).hexdigest()
    url = 'https://www.gravatar.com/avatar/%s?d=%s' % (md5, _cachedDefaultImage)

    user['gravatar_baseUrl'] = url
    ModelImporter.model('user').save(user)

    return url


@access.public
@loadmodel(model='user', level=AccessType.READ)
def getGravatar(user, params):
    size = int(params.get('size', 64))

    if user.get('gravatar_baseUrl'):
        baseUrl = user['gravatar_baseUrl']
    else:
        baseUrl = computeBaseUrl(user)

    raise cherrypy.HTTPRedirect(baseUrl + '&s=%d' % size)
getGravatar.description = (
    Description('Redirects to the gravatar image for a user.')
    .param('id', 'The ID of the user.', paramType='path')
    .param('size', 'Size in pixels for the image (default=64).', required=False,
           dataType='int')
    .notes('This should only be used if the gravatar_baseUrl property of'))


def validateSettings(event):
    if event.info['key'] == PluginSettings.DEFAULT_IMAGE:
        event.preventDefault().stopPropagation()

        # TODO should we update user collection to remove gravatar_baseUrl vals?
        # Invalidate cached default image since setting changed
        global _cachedDefaultImage
        _cachedDefaultImage = None


def userUpdate(event):
    """
    Called when the user document is being changed. If the email field changes,
    we wipe the cached gravatar URL so it will be recomputed on next request.
    """
    if 'email' in event.info['params']:
        user = ModelImporter.model('user').load(event.info['id'], force=True)
        if (user['email'] != event.info['params']['email'] and
                user.get('gravatar_baseUrl')):
            del user['gravatar_baseUrl']
            ModelImporter.model('user').save(user)


def load(info):
    info['apiRoot'].user.route('GET', (':id', 'gravatar'), getGravatar)

    ModelImporter.model('user').exposeFields(
        level=AccessType.READ, fields='gravatar_baseUrl')

    events.bind('model.setting.validate', 'gravatar', validateSettings)
    events.bind('rest.put.user/:id.before', 'gravatar', userUpdate)
