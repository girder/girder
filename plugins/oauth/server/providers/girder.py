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
from girder.constants import TokenScope
from girder.exceptions import RestException
from girder.models.setting import Setting
from .base import ProviderBase
from .. import constants


class Girder(ProviderBase):
    _AUTH_SCOPES = [TokenScope.USER_INFO_READ]

    def getClientIdSetting(self):
        return Setting().get(constants.PluginSettings.GIRDER_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(constants.PluginSettings.GIRDER_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        loginUrl = Setting().get(constants.PluginSettings.GIRDER_LOGIN_URL)
        clientId = Setting().get(constants.PluginSettings.GIRDER_CLIENT_ID)

        if clientId is None:
            raise Exception('No Girder client ID setting is present.')
        if loginUrl is None:
            raise Exception('No Girder login URL setting is present.')

        query = urllib.parse.urlencode({
            'clientId': clientId,
            'redirect': '/'.join((getApiUrl(), 'oauth', 'girder', 'callback')),
            'state': state,
            'scope': ' '.join(cls._AUTH_SCOPES)
        })
        return '%s?%s' % (loginUrl, query)

    def getToken(self, code):
        apiUrl = Setting().get(constants.PluginSettings.GIRDER_API_URL)
        return self._getJson(method='POST', url='/'.join((apiUrl, 'oauth_client', 'token')), data={
            'clientId': self.clientId,
            'code': code,
            'secret': self.clientSecret,
            'redirect': self.redirectUri
        })

    def getUser(self, token):
        apiUrl = Setting().get(constants.PluginSettings.GIRDER_API_URL)
        headers = {'Girder-Token': token['token']}
        user = self._getJson(method='GET', url='/'.join((apiUrl, 'user', 'me')), headers=headers)

        if user is None or user.get('_modelType') != 'user':
            raise RestException('Invalid Girder authentication token.')

        return self._createOrReuseUser(
            user['_id'], user['email'], user['firstName'], user['lastName'], user['login'])
