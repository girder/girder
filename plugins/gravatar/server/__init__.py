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


class PluginSettings(object):
    DEFAULT_IMAGE = 'gravatar.default_image'


def getDefaultImage():
    return ModelImporter.model('setting').get(
        PluginSettings.DEFAULT_IMAGE, default='identicon')


@access.public
@loadmodel(model='user', level=AccessType.READ)
def getGravatar(user, params):
    size = int(params.get('size', 64))
    md5 = hashlib.md5(user['email']).hexdigest()
    default = getDefaultImage() or 'identicon'
    url = 'https://www.gravatar.com/avatar/%s?d=%s&s=%s' % (md5, default, size)
    raise cherrypy.HTTPRedirect(url)
getGravatar.description = (
    Description('Redirects to the gravatar image for a user.')
    .param('id', 'The ID of the user.', paramType='path')
    .param('size', 'Size in pixels for the image (default=64).', required=False,
           dataType='int'))


def validateSettings(event):
    if event.info['key'] == PluginSettings.DEFAULT_IMAGE:
        event.preventDefault().stopPropagation()


def load(info):
    events.bind('model.setting.validate', 'gravatar', validateSettings)
    info['apiRoot'].user.route('GET', (':id', 'gravatar'), getGravatar)
