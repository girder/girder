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


class Box(ProviderBase):
    _AUTH_URL = 'https://account.box.com/api/oauth2/authorize'
    _TOKEN_URL = 'https://api.box.com/oauth2/token'
    _API_USER_URL = 'https://api.box.com/2.0/users/me'

    def getClientIdSetting(self):
        return Setting().get(constants.PluginSettings.BOX_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(constants.PluginSettings.BOX_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(constants.PluginSettings.BOX_CLIENT_ID)

        if clientId is None:
            raise Exception('No Box client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'box', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
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
            'Authorization': 'Bearer %s' % token['access_token'],
            'Accept': 'application/json'
        }

        # Get user's email address
        resp = self._getJson(method='GET', url=self._API_USER_URL, headers=headers)
        email = resp.get('login')
        if not email:
            raise RestException(
                'Box did not return user information.', code=502)

        # Get user's OAuth2 ID, login, and name
        oauthId = resp.get('id')
        if not oauthId:
            raise RestException('Box did not return a user ID.', code=502)

        names = resp.get('name').split()
        firstName, lastName = names[0], names[-1]
        return self._createOrReuseUser(oauthId, email, firstName, lastName)
