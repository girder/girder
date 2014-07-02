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
import os
import urllib

from girder.utility.model_importer import ModelImporter
from girder.api.describe import Description
from girder.api.rest import Resource, RestException
from . import constants


class OAuth(Resource):
    def __init__(self):
        self.resourceName = 'oauth'

        self.route('GET', ('google', 'url'), self.googleUrl)
        self.route('GET', ('google', 'callback'), self.googleCallback)

    def googleUrl(self, params):
        clientId = self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_ID)

        if clientId is None:
            raise Exception('No Google client ID setting is present.')

        callbackUrl = os.path.join(os.path.dirname(cherrypy.url()), 'callback')

        query = urllib.urlencode({
            'response_type': 'code',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'scope': ' '.join(constants.GOOGLE_SCOPES)
        })

        return '{}?{}'.format(constants.GOOGLE_URL, query)
    googleUrl.description = (
        Description('Get the URL required to initiate Google OAuth.'))


    def googleCallback(self, params):
        pass  # TODO implement callback
    googleCallback.description = None
