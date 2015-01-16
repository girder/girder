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

import re
import requests

from girder.api.rest import RestException
from girder.constants import SettingKey
from girder.utility import config, model_importer
from . import constants


def _deriveLogin(email, userModel):
    """
    Attempt to derive a sensible login from the given email. If this fails,
    it will return None and the caller must use some unique default.
    """
    login = email.split('@')[0]  # Try first part of email address
    regex = config.getConfig()['users']['login_regex']
    if not re.match(regex, login):
        login = re.sub('[\W_]+', '', login)  # Remove non-alphanumeric chars

    if not re.match(regex, login):
        return None  # Still doesn't match regex, we're hosed

    cursor = userModel.find({'login': login}, limit=1)
    if cursor.count(True) > 0:
        return None  # This is already taken, we're hosed

    return login


def _verifyOpenRegistration():
    """
    Raises a REST exception if registration policy on the server is not set to
    'open'. This should be called by the provider-specific code in the case when
    a user logs in with an email that is not already tied to an existing user.
    """
    policy = model_importer.ModelImporter().model('setting').get(
        SettingKey.REGISTRATION_POLICY, default='open')
    if policy != 'open':
        raise RestException(
            'Registration on this instance is closed. Contact an administrator '
            'to create an account for you.')


class Google(model_importer.ModelImporter):
    def __init__(self, clientId, clientSecret, redirectUri):
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.redirectUri = redirectUri

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

        cursor = self.model('user').find({'email': email}, limit=1)
        if cursor.count(True) == 0:
            _verifyOpenRegistration()
            login = _deriveLogin(email, self.model('user'))
            if login is None:
                login = 'googleuser' + resp['id']
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
