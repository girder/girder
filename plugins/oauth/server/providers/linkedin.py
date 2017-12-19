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


class LinkedIn(ProviderBase):
    _AUTH_URL = 'https://www.linkedin.com/uas/oauth2/authorization'
    _AUTH_SCOPES = ['r_basicprofile', 'r_emailaddress']
    _TOKEN_URL = 'https://www.linkedin.com/uas/oauth2/accessToken'
    _API_USER_URL = 'https://api.linkedin.com/v1/people/~'
    _API_USER_FIELDS = ('id', 'emailAddress', 'firstName', 'lastName')

    def getClientIdSetting(self):
        return Setting().get(constants.PluginSettings.LINKEDIN_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(constants.PluginSettings.LINKEDIN_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(constants.PluginSettings.LINKEDIN_CLIENT_ID)

        if clientId is None:
            raise Exception('No LinkedIn client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'linkedin', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': ' '.join(cls._AUTH_SCOPES)
        })
        return '?'.join((cls._AUTH_URL, query))

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri,
        }
        resp = self._getJson(method='POST', url=self._TOKEN_URL,
                             data=params,
                             headers={'Accept': 'application/json'})
        return resp

    def getUser(self, token):
        headers = {
            'Authorization': 'Bearer %s' % token['access_token'],
            'Accept': 'application/json'
        }

        # Get user's OAuth2 ID, email, and name
        # For privacy and efficiency, fetch only the specific needed fields
        # https://developer.linkedin.com/docs/signin-with-linkedin
        url = '%s:(%s)?%s' % (
            self._API_USER_URL,
            ','.join(self._API_USER_FIELDS),
            urllib.parse.urlencode({'format': 'json'})
        )
        resp = self._getJson(method='GET', url=url, headers=headers)

        oauthId = resp.get('id')
        if not oauthId:
            raise RestException('LinkedIn did not return user ID.', code=502)

        email = resp.get('emailAddress')
        if not email:
            raise RestException(
                'This LinkedIn user has no registered email address.', code=502)

        # Get user's name
        firstName = resp.get('firstName', '')
        lastName = resp.get('lastName', '')

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
