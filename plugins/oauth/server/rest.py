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

from girder.constants import AccessType
from girder.api.describe import Description
from girder.api.rest import Resource
from girder.api import access
from . import constants, providers


class OAuth(Resource):
    def __init__(self):
        self.resourceName = 'oauth'

        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', (':provider', 'callback'), self.callback)

    def _sendCsrfToken(self, redirect):
        csrfToken = self.model('token').createToken(days=0.25)

        cookie = cherrypy.response.cookie
        cookie['oauthLogin'] = json.dumps({
            'redirect': redirect,
            'token': str(csrfToken['_id'])
        })
        cookie['oauthLogin']['path'] = '/'
        cookie['oauthLogin']['expires'] = 3600 * 6

    def _validateCsrfToken(self, redirect):
        """
        Tests the CSRF token value in the cookie to authenticate the user as
        the originator of the OAuth login. Raises an Exception if the token
        is invalid.
        """
        cookie = cherrypy.request.cookie
        if 'oauthLogin' not in cookie:
            raise Exception('No CSRF cookie (state="%s").' % redirect)

        info = json.loads(cookie['oauthLogin'].value)

        cookie = cherrypy.response.cookie
        cookie['oauthLogin'] = ''
        cookie['oauthLogin']['path'] = '/'
        cookie['oauthLogin']['expires'] = 0

        if info['redirect'] != redirect:
            raise Exception('Redirect does not match original value (%s, %s)' %
                            (info['redirect'], redirect))

        token = self.model('token').load(
            info['token'], objectId=False, level=AccessType.READ)

        if token is None:
            raise Exception('Invalid CSRF token (state="%s").' % redirect)

        self.model('token').remove(token)

        if token['expires'] < datetime.datetime.utcnow():
            raise Exception('Expired CSRF token (state="%s").' % redirect)

    @access.public
    def listProviders(self, params):
        self.requireParams(('redirect',), params)
        redirect = params['redirect']

        enabled = self.model('setting').get(
            constants.PluginSettings.PROVIDERS_ENABLED)

        self._sendCsrfToken(redirect)

        info = {}
        for provider in enabled:
            if provider in providers.idMap:
                info[provider] = providers.idMap[provider].getUrl(redirect)

        return info
    listProviders.description = (
        Description('Get the set of supported OAuth providers and their URLs.')
        .notes('Will be returned as an object mapping provider name to the '
               'corresponding URL to direct the user agent to.')
        .param('redirect', 'Where the user should be redirected upon completion'
               ' of the OAuth flow.'))

    @access.public
    def callback(self, provider, params):
        self.requireParams(('state', 'code'), params)

        redirect, code = params['state'], params['code']
        self._validateCsrfToken(redirect)

        if 'error' in params:
            raise cherrypy.HTTPRedirect(redirect)

        user = providers.idMap[provider](cherrypy.url()).getUser(code)

        self.sendAuthTokenCookie(user)

        raise cherrypy.HTTPRedirect(redirect)
    callback.description = None
