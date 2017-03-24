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
    def __init__(self, redirectUri, clientId=None, clientSecret=None,
                 storeToken=False):
        """
        Base class for OAuth2 providers. The purpose of these classes is to
        perform the user information lookup to their respective provider
        services in order to return a Girder user given an OAuth2 code that was
        sent to us via a callback.

        :param clientId: The client ID for the given OAuth2 provider.
        :type clientId: str
        :param clientSecret: The client secret for the given OAuth2 provider.
        :type clientSecret: str
        :param redirectUri: The redirect URI used in this OAuth2 flow.
        :type redirectUri: str
        :param storeToken: Store the access token obtained in this OAuth2 flow.
        :type storeToken: boolean
        """
        self.clientId = clientId or self.getClientIdSetting()
        self.clientSecret = clientSecret or self.getClientSecretSetting()
        self.storeToken = storeToken or self.getStoreTokenSetting()
        self.redirectUri = redirectUri

    @classmethod
    def getProviderName(cls, external=False):
        providerName = cls.__name__
        if external:
            return providerName
        else:
            return providerName.lower()

    def getClientIdSetting(self):
        raise NotImplementedError()

    def getClientSecretSetting(self):
        raise NotImplementedError()

    def getStoreTokenSetting(self):
        raise NotImplementedError()

    @classmethod
    def getUrl(cls, state):
        """
        Return the URL to start the OAuth2 authentication flow with an external
        provider.

        This abstract function must be reimplemented by each provider.

        :param state: A unique string, used to prevent CSRF and store other
        state information. This string should not be URL-encoded (that must be
        done in this method).
        :return: An external absolute URL to the start point for this provider's
        OAuth2 flow.
        """
        raise NotImplementedError()

    def getToken(self, code):
        raise NotImplementedError()

    def getUser(self, token):
        """
        Returns a user via this OAuth2 provider, given an OAuth2 access token.

        Subclasses must implement this to retrieve a provider-specific unique
        identifier, email address, first name, last name, and optionally a
        login name from the OAuth2 provider, and then call
        self._createOrReuseUser with that information to lookup or create a
        corresponding Girder user.

        :param token: The current OAuth2 access token.
        :returns: The user document corresponding to this user.
        """
        raise NotImplementedError()

    @staticmethod
    def _getJson(**kwargs):
        """
        Make an HTTP request using the specified kwargs, then parse it as JSON
        and return the value. If an error occurs, this raises an appropriate
        exception containing the information.
        """
        resp = requests.request(**kwargs)
        content = resp.content

        if isinstance(content, six.binary_type):
            content = content.decode('utf8')

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise RestException(
                'Got %s code from provider, response="%s".' % (
                    resp.status_code, content
                ), code=502)

        try:
            return json.loads(content)
        except ValueError:
            raise RestException('Non-JSON response: %s' % content, code=502)

    @classmethod
    def _createOrReuseUser(cls, oauthId, email, firstName, lastName,
                           oauthHeaders, userName=None):
        providerName = cls.getProviderName()

        # Try finding by ID first, since a user can change their email address
        query = {
            # PyMongo may not properly support full embedded document queries,
            # since the object order matters (and Python dicts are unordered),
            # so search by individual embedded fields
            'oauth.provider': providerName,
            'oauth.id': oauthId
        }
        if providerName == 'google':
            # The Google provider was previously stored as capitalized, and
            # legacy databases may still have these entries
            query['oauth.provider'] = {'$in': ['google', 'Google']}
        user = cls.model('user').findOne(query)
        setId = not user

        # Existing users using OAuth2 for the first time will not have an ID
        if not user:
            user = cls.model('user').findOne({'email': email})

        dirty = False
        # Create the user if it's still not found
        if not user:
            policy = cls.model('setting').get(SettingKey.REGISTRATION_POLICY)
            if policy == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')
            login = cls._deriveLogin(email, firstName, lastName, userName)

            user = cls.model('user').createUser(
                login=login, password=None, firstName=firstName,
                lastName=lastName, email=email)
        else:
            # Migrate from a legacy format where only 1 provider was stored
            if isinstance(user.get('oauth'), dict):
                user['oauth'] = [user['oauth']]
                dirty = True
            # Update user data from provider
            if email != user['email']:
                user['email'] = email
                dirty = True
            # Don't set names to empty string
            if firstName != user['firstName'] and firstName:
                user['firstName'] = firstName
                dirty = True
            if lastName != user['lastName'] and lastName:
                user['lastName'] = lastName
                dirty = True
        if setId:
            user.setdefault('oauth', []).append(
                {
                    'provider': providerName,
                    'id': oauthId
                })
            dirty = True

        currentOAuth = next(_ for _ in user['oauth'] if _['id'] == oauthId)
        if oauthHeaders:
            currentOAuth['authHeaders'] = oauthHeaders
            dirty = True
        else:
            if 'authHeaders' in currentOAuth:
                currentOAuth.pop('authHeaders')
                dirty = True

        if dirty:
            user = cls.model('user').save(user)

        return user

    @classmethod
    def _generateLogins(cls, email, firstName, lastName, userName=None):
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

    @classmethod
    def _deriveLogin(cls, email, firstName, lastName, userName=None):
        """
        Attempt to automatically create a login name from existing user
        information from OAuth2 providers. Attempts to generate it from the
        username on the provider, the email address, or first and last name. If
        not possible, returns None and it is left to the caller to generate
        their own login for the user or choose to fail.

        :param email: The email address.
        :type email: str
        """
        # Note, the user's OAuth2 ID should never be used to form a login name,
        # as many OAuth2 services consider that to be private data
        for login in cls._generateLogins(email, firstName, lastName, userName):
            login = login.lower()
            if cls._testLogin(login):
                return login

        raise Exception('Could not generate a unique login name for %s (%s %s)'
                        % (email, firstName, lastName))

    @classmethod
    def _testLogin(cls, login):
        """
        When attempting to generate a username, use this to test if the given
        name is valid.
        """
        regex = config.getConfig()['users']['login_regex']

        # Still doesn't match regex, we're hosed
        if not re.match(regex, login):
            return False

        # See if this is already taken.
        user = cls.model('user').findOne({'login': login})

        return not user
