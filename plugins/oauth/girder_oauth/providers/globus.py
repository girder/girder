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

from six.moves import urllib

from girder.api.rest import getApiUrl
from girder.exceptions import RestException
from girder.models.setting import Setting
from .base import ProviderBase
from .. import constants


class Globus(ProviderBase):
    _AUTH_URL = 'https://auth.globus.org/v2/oauth2/authorize'
    _AUTH_SCOPES = ['urn:globus:auth:scope:auth.globus.org:view_identities',
                    'openid', 'profile', 'email']
    _TOKEN_URL = 'https://auth.globus.org/v2/oauth2/token'
    _API_USER_URL = 'https://auth.globus.org/v2/oauth2/userinfo'

    def getClientIdSetting(self):
        return Setting().get(constants.PluginSettings.GLOBUS_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(constants.PluginSettings.GLOBUS_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(constants.PluginSettings.GLOBUS_CLIENT_ID)

        if clientId is None:
            raise Exception('No Globus client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'globus', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': ' '.join(cls._AUTH_SCOPES)
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri
        }
        resp = self._getJson(method='POST', url=self._TOKEN_URL,
                             data=params,
                             headers={'Accept': 'application/json'})
        if 'error' in resp:
            raise RestException(
                'Got an error exchanging token from provider: "%s".' % resp,
                code=502)
        return resp

    def getUser(self, token):
        headers = {
            'Authorization': 'Bearer {}'.format(token['access_token'])
        }

        resp = self._getJson(method='GET', url=self._API_USER_URL,
                             headers=headers)

        oauthId = resp.get('sub')
        if not oauthId:
            raise RestException(
                'Globus identity did not return a valid ID.', code=502)

        email = resp.get('email')
        if not email:
            raise RestException(
                'Globus identity did not return a valid email.', code=502)

        name = resp['name'].split()
        firstName = name[0]
        lastName = name[-1]

        return self._createOrReuseUser(oauthId, email, firstName, lastName)
