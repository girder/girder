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

import json
import re
import requests
import six

from girder.api.rest import RestException
from girder.constants import SettingKey
from girder.utility import config, model_importer


class ProviderBase(model_importer.ModelImporter):
    def __init__(self, redirectUri, clientId=None, clientSecret=None):
        """
        Base class for OAuth providers. The purpose of these classes is to
        perform the user information lookup to their respective provider
        services in order to return a Girder user given an OAuth code that was
        sent to us via a callback.

        :param clientId: The client ID for the given OAuth provider.
        :type clientId: str
        :param clientSecret: The client secret for the given OAuth provider.
        :type clientSecret: str
        :param redirectUri: The redirect URI used in this OAuth flow.
        :type redirectUri: str
        """
        self.clientId = clientId or self.getClientIdSetting()
        self.clientSecret = clientSecret or self.getClientSecretSetting()
        self.redirectUri = redirectUri

    def getClientIdSetting(self):
        raise NotImplementedError()

    def getClientSecretSetting(self):
        raise NotImplementedError()

    @classmethod
    def getUrl(cls, state):
        raise NotImplementedError()

    def getJson(self, **kwargs):
        """
        Make an HTTP request using the specified kwargs, then parse it as JSON
        and return the value. If an error occurs, this raises an appropriate
        exception containing the information.
        """
        resp = requests.request(**kwargs)
        content = resp.content

        if not isinstance(content, six.text_type):
            content = content.decode('utf8')

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise RestException(
                'Got %s from %s, response="%s".' % (
                    resp.status_code, kwargs['url'], content
                ), code=502)

        try:
            return json.loads(content)
        except ValueError:
            raise RestException('Non-JSON response: %s' % content, code=502)

    def getUser(self, code):
        """
        Returns a user via this OAuth provider given an OAuth code. Subclasses
        must implement this to retrieve an email address, first name, last name,
        and optionally a login name from the OAuth provider, and then call
        self.createOrReuseUser with that information to lookup or create a
        corresponding Girder user.
        """
        raise NotImplementedError()

    def createOrReuseUser(self, email, firstName, lastName, userName=None):
        cursor = self.model('user').find({'email': email}, limit=1)
        if cursor.count(True) == 0:
            policy = self.model('setting').get(SettingKey.REGISTRATION_POLICY)
            if policy != 'open':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')
            login = self.deriveLogin(email, firstName, lastName, userName)

            user = self.model('user').createUser(
                login=login, password=None, firstName=firstName,
                lastName=lastName, email=email)
        else:
            user = cursor[0]
            user['firstName'] = firstName
            user['lastName'] = lastName

        return user

    def generateLogins(self, email, firstName, lastName, userName=None):
        """
        Generate a series of reasonable login names for a new user based on
        their basic information sent to us by the provider.
        """
        # If they have a username on the other service, try that
        if userName:
            yield userName
            userName = re.sub('[\W_]+', '', userName)
            yield userName

            for i in range(1, 6):
                yield '%s%d' % (userName, i)

        # Next try to use the prefix from their email address
        prefix = email.split('@')[0]
        yield prefix
        yield re.sub('[\W_]+', '', prefix)

        # Finally try to use their first and last name
        yield '%s%s' % (firstName, lastName)

        for i in range(1, 6):
            yield '%s%s%d' % (firstName, lastName, i)

    def deriveLogin(self, email, firstName, lastName, userName=None):
        """
        Attempt to automatically create a login name from existing user
        information from OAuth providers. Attempts to generate it from the
        username on the provider, the email address, or first and last name. If
        not possible, returns None and it is left to the caller to generate
        their own login for the user or choose to fail.

        :param email: The email address.
        :type email: str
        """
        for login in self.generateLogins(email, firstName, lastName, userName):
            login = login.lower()
            if self.testLogin(login):
                return login

        return None

    def testLogin(self, login):
        """
        When attempting to generate a username, use this to test if the given
        name is valid.
        """
        regex = config.getConfig()['users']['login_regex']

        # Still doesn't match regex, we're hosed
        if not re.match(regex, login):
            return False

        # See if this is already taken.
        cursor = self.model('user').find({'login': login}, limit=1)
        if cursor.count(True) > 0:
            return False

        return True
