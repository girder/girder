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
import json
import os
import urllib

from girder.constants import AccessType
from girder.api.describe import Description
from girder.api.rest import Resource
from girder.api import access
from . import constants, providers


class OAuth(Resource):
    def __init__(self):
        self.resourceName = 'oauth'

        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', ('google', 'callback'), self.googleCallback)

    @access.public
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

        callbackUrl = '/'.join((
            os.path.dirname(cherrypy.url()), 'google', 'callback'))

        query = urllib.urlencode({
            'response_type': 'code',
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': redirect,
            'scope': ' '.join(constants.GOOGLE_SCOPES)
        })

        self._setCsrfToken(redirect)

        return '{}?{}'.format(constants.GOOGLE_AUTH_URL, query)

    @access.public
    def googleCallback(self, params):
        self.requireParams(('state', 'code'), params)

        redirect = params['state']
        self._validateCsrfToken(redirect)

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

    def _setCsrfToken(self, redirect):
        """
        Generate an anti-CSRF token and set it in a cookie for the user. It will
        be verified upon completion of the OAuth login flow.
        This can be used consistently across all of the OAuth providers.
        """
        csrfToken = self.model('token').createToken(days=0.25)

        cookie = cherrypy.response.cookie
        cookie['oauthLogin'] = json.dumps({
            'redirect': redirect,
            'token': str(csrfToken['_id'])
        })
        cookie['oauthLogin']['path'] = '/'
        cookie['oauthLogin']['expires'] = 3600 * 6  # 0.25 days

    def _validateCsrfToken(self, redirect):
        """
        Tests the CSRF token value in the cookie to authenticate the user as
        the originator of the OAuth login. Raises an Exception if the token
        is invalid.
        """
        cookie = cherrypy.request.cookie
        if 'oauthLogin' not in cookie:
            raise Exception('No CSRF cookie (state="{}").'.format(redirect))

        info = json.loads(cookie['oauthLogin'].value)

        cookie = cherrypy.response.cookie
        cookie['oauthLogin'] = ''
        cookie['oauthLogin']['path'] = '/'
        cookie['oauthLogin']['expires'] = 0

        if info['redirect'] != redirect:
            raise Exception('Redirect does not match original value ({}, {})'
                            .format(info['redirect'], redirect))

        token = self.model('token').load(
            info['token'], objectId=False, level=AccessType.READ)

        if token is None:
            raise Exception('Invalid CSRF token (state="{}").'.format(redirect))

        self.model('token').remove(token)

        if token['expires'] < datetime.datetime.utcnow():
            raise Exception('Expired CSRF token (state="{}").'.format(redirect))
