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

from girder.api.rest import getApiUrl
from girder.plugins.oauth import constants
from .base import ProviderBase
from six.moves import urllib


class GitHub(ProviderBase):
    def getClientIdSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GITHUB_CLIENT_ID)

    def getClientSecretSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GITHUB_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = cls.model('setting').get(
            constants.PluginSettings.GITHUB_CLIENT_ID)

        if clientId is None:
            raise Exception('No GitHub client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'github', 'callback'))

        query = urllib.parse.urlencode({
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': ','.join(constants.GITHUB_SCOPES)
        })

        return '?'.join((constants.GITHUB_AUTH_URL, query))

    def getUser(self, code):
        params = {
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri
        }
        resp = self.getJson(method='POST', url=constants.GITHUB_TOKEN_URL,
                            data=params, headers={
                                'Accept': 'application/json'
                            })

        headers = {
            'Authorization': 'token %s' % resp['access_token'],
            'Accept': 'application/json'
        }

        resp = self.getJson(method='GET', url=constants.GITHUB_EMAILS_URL,
                            headers=headers)
        email = None
        for email in resp:
            if email['primary']:
                break

        if not email:
            raise Exception('This GitHub user has no registered emails.')

        email = email['email']
        resp = self.getJson(method='GET', url=constants.GITHUB_USER_URL,
                            headers=headers)

        login = resp['login']
        names = resp['name'].split()
        first, last = names[0], names[-1]

        user = self.createOrReuseUser(email, first, last, login)
        user['oauth'] = {
            'provider': 'GitHub',
            'id': resp['id']
        }

        return self.model('user').save(user)
