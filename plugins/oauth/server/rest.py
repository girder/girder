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
import datetime
import os
import urllib

from girder import logger
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder.api.describe import Description
from girder.api.rest import Resource, RestException
from . import constants, providers


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
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': self._setSecureState(redirect),
            'scope': ' '.join(constants.GOOGLE_SCOPES)
        })

        return '{}?{}'.format(constants.GOOGLE_AUTH_URL, query)

    def googleCallback(self, params):
        self.requireParams(('state', 'code'), params)
        redirect = self._parseSecureState(params['state'])

        if 'error' in params:
            raise cherrypy.HTTPRedirect(redirect)

        clientId = self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_ID)
        clientSecret = self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_SECRET)

        user = providers.Google(
            clientId, clientSecret, cherrypy.url()).getUser(params['code'])

        self.sendAuthTokenCookie(user)

        raise cherrypy.HTTPRedirect(redirect)
    googleCallback.description = None

    def _setSecureState(self, redirect):
        """
        Adds CSRF protection to create a state parameter that will later be
        consumed by _getSecureRedirect upon completion of the OAuth login flow.
        This can be used consistently across all of the OAuth providers.
        """
        csrfToken = self.model('token').createToken(days=0.25)
        return '{}_{}'.format(csrfToken['_id'], redirect)

    def _parseSecureState(self, state):
        """
        Returns the URL that the user should be directed to based on the state
        parameter, performing the CSRF mitigation in the process and deleting
        the token upon success.
        """
        csrfToken, redirect = state.split('_', 1)
        token = self.model('token').load(
            csrfToken, objectId=False, level=AccessType.READ)

        if token is None:
            raise Exception('Invalid CSRF token (state="{}").'.format(state))

        self.model('token').remove(token)

        if token['expires'] < datetime.datetime.now():
            raise Exception('Expired CSRF token (state="{}").'.format(state))

        return redirect
