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

from girder.api.rest import RestException, getApiUrl
from girder.models.model_base import AccessType
from girder.plugins.oauth import constants
from . import ProviderBase
from six.moves import urllib


class Google(ProviderBase):
    def getClientIdSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_ID)

    def getClientSecretSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = cls.model('setting').get(
            constants.PluginSettings.GOOGLE_CLIENT_ID)

        if clientId is None:
            raise Exception('No Google client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'google', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': ' '.join(constants.GOOGLE_SCOPES)
        })

        return '?'.join((constants.GOOGLE_AUTH_URL, query))

    def getUser(self, code):
        """
        Given an authorization code from an oauth callback, retrieve the user
        information, creating or updating our user record if necessary.

        :param code: The authorization code from google.
        :returns: The user document corresponding to this google user.
        """
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri
        }
        resp = self.getJson(method='POST', url=constants.GOOGLE_TOKEN_URL,
                            data=params)

        headers = {
            'Authorization': ' '.join((
                resp['token_type'], resp['access_token']))
        }
        resp = self.getJson(method='GET', url=constants.GOOGLE_USER_URL,
                            headers=headers)

        for email in resp['emails']:
            if email['type'] == 'account':
                break
        email = email['value']

        firstName = resp['name'].get('givenName', '')
        lastName = resp['name'].get('familyName', '')

        user = self.createOrReuseUser(email, firstName, lastName)
        user['oauth'] = {
            'provider': 'Google',
            'id': resp['id']
        }

        return self.model('user').save(user)
