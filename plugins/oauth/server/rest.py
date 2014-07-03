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

        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', ('google', 'callback'), self.googleCallback)

    def listProviders(self, params):
        """
        TODO Once we have multiple providers, this list should be dynamically
        built based on the selection of which providers are enabled on the
        plugin config page.
        """
        self.requireParams(('redirect',), params)
        return {
            'Google': self._getGoogleUrl(params['redirect'])
        }
    listProviders.description = (
        Description('Get the set of supported OAuth providers and their URLs.')
        .notes('Will be returned as an object mapping provider name to the '
               'corresponding URL to direct the user agent to.')
        .param('redirect', 'Where the user should be redirected upon completion'
               ' of the OAuth flow.'))

    def _getGoogleUrl(self, redirect):
        clientId = self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_ID)

        if clientId is None:
            raise Exception('No Google client ID setting is present.')

        callbackUrl = os.path.join(
            os.path.dirname(cherrypy.url()), 'google', 'callback')

        query = urllib.urlencode({
            'response_type': 'code',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': redirect,
            'scope': ' '.join(constants.GOOGLE_SCOPES)
        })

        return '{}?{}'.format(constants.GOOGLE_URL, query)

    def googleCallback(self, params):
        pass  # TODO implement callback
    googleCallback.description = None
