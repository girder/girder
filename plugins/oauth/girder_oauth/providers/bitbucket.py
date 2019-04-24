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


class Bitbucket(ProviderBase):
    _AUTH_URL = 'https://bitbucket.org/site/oauth2/authorize'
    _AUTH_SCOPES = ['account']
    _TOKEN_URL = 'https://bitbucket.org/site/oauth2/access_token'
    _API_USER_URL = 'https://api.bitbucket.org/2.0/user'
    _API_EMAILS_URL = 'https://api.bitbucket.org/2.0/user/emails'

    def getClientIdSetting(self):
        return Setting().get(constants.PluginSettings.BITBUCKET_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(constants.PluginSettings.BITBUCKET_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(constants.PluginSettings.BITBUCKET_CLIENT_ID)

        if clientId is None:
            raise Exception('No Bitbucket client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'bitbucket', 'callback'))

        query = urllib.parse.urlencode({
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'response_type': 'code',
            'scope': ','.join(cls._AUTH_SCOPES)
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'code': code,
            'client_id': self.clientId,
            'grant_type': 'authorization_code',
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri,
        }
        # Bitbucket returns application/x-www-form-urlencoded unless
        # otherwise specified with Accept
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
            'Authorization': 'Bearer {}'.format(token['access_token']),
            'Accept': 'application/json'
        }

        # Get user's email address
        # In the unlikely case that a user has more than 30 email addresses,
        # this HTTP request might have to be made multiple times with
        # pagination
        resp = self._getJson(method='GET', url=self._API_EMAILS_URL,
                             headers=headers)
        emails = [
            email.get('email')
            for email in resp['values']
            if email.get('is_primary') and email.get('is_confirmed')
        ]
        if not emails:
            raise RestException(
                'This Bitbucket user has no registered email address.',
                code=502)
        # There should never be more than one primary email
        email = emails[0]

        # Get user's OAuth2 ID, login, and name
        resp = self._getJson(method='GET', url=self._API_USER_URL,
                             headers=headers)
        oauthId = resp.get('uuid')
        if not oauthId:
            raise RestException('Bitbucket did not return a user ID.', code=502)

        login = resp.get('username', None)

        names = (resp.get('display_name') or login).split()
        firstName, lastName = names[0], names[-1]

        user = self._createOrReuseUser(oauthId, email, firstName, lastName, login)
        return user
