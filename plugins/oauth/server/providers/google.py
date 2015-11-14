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

from girder.api.rest import getApiUrl, RestException
from .base import ProviderBase
from .. import constants


class Google(ProviderBase):
    _AUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
    _AUTH_SCOPES = ('profile', 'email')
    _TOKEN_URL = 'https://accounts.google.com/o/oauth2/token'
    _API_USER_URL = 'https://www.googleapis.com/plus/v1/people/me'
    _API_USER_FIELDS = ('id', 'emails', 'name')

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
                             data=params)
        return resp

    def getUser(self, token):
        headers = {
            'Authorization': ' '.join((
                token['token_type'], token['access_token']))
        }
        # For privacy and efficiency, fetch only the specific needed fields
        # https://developers.google.com/+/web/api/rest/#partial-response
        query = urllib.parse.urlencode({
            'fields': ','.join(self._API_USER_FIELDS)
        })
        resp = self._getJson(method='GET',
                             url='%s?%s' % (self._API_USER_URL, query),
                             headers=headers)

        # Get user's OAuth2 ID
        oauthId = resp.get('id')
        if not oauthId:
            raise RestException(
                'Google Plus did not return a user ID.', code=502)

        # Get user's email address
        # Prefer email address with 'account' type
        emails = [
            email.get('value')
            for email in resp.get('emails', [])
            if email.get('type') == 'account'
        ]
        if not emails:
            # If an 'account' email can't be found, consider them all
            emails = [
                email.get('value')
                for email in resp.get('emails', [])
            ]
        if emails:
            # Even if there are multiple emails, just use the first one
            email = emails[0]
        else:
            raise RestException(
                'This Google Plus user has no available email address.',
                code=502)

        # Get user's name
        firstName = resp.get('name', {}).get('givenName', '')
        lastName = resp.get('name', {}).get('familyName', '')

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
