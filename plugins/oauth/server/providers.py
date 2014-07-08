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

import requests

from girder.utility.model_importer import ModelImporter
from . import constants


class Google(ModelImporter):
    def __init__(self, clientId, clientSecret, redirectUri):
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.redirectUri = redirectUri

    def getUser(self, code):
        """
        Given an authorization code from an oauth callback, retrieve the user
        information, creating or updating our user record if necessary.
        :param code: The authorization code from google.
        :returns: The user document corresponding to thsi google user.
        """
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri
        }
        resp = requests.post(constants.GOOGLE_TOKEN_URL, data=params).json()

        headers = {
            'Authorization': '{} {}'.format(
                resp['token_type'], resp['access_token'])
        }
        resp = requests.get(constants.GOOGLE_USER_URL, headers=headers).json()

        for email in resp['emails']:
            if email['type'] == 'account':
                break
        email = email['value']

        firstName = resp['name'].get('givenName', '')
        lastName = resp['name'].get('familyName', '')
        login = 'googleuser' + resp['id']
        cursor = self.model('user').find({'email': email}, limit=1)
        if cursor.count(True) == 0:
            user = self.model('user').createUser(
                login=login, password=None, firstName=firstName,
                lastName=lastName, email=email)
        else:
            user = cursor.next()
            user['firstName'] = firstName
            user['lastName'] = lastName

        user['oauth'] = {
            'provider': 'Google',
            'id': resp['id']
        }
        self.model('user').save(user)

        return user
