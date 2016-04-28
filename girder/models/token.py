#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import datetime
import six

from girder.constants import AccessType, SettingKey, TokenScope
from girder.utility import genToken
from .model_base import AccessControlledModel


class Token(AccessControlledModel):
    """
    This model stores session tokens for user authentication.
    """
    def initialize(self):
        self.name = 'token'
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))
        self.ensureIndex('apiKeyId')

    def validate(self, doc):
        # Remove any duplicate scopes
        doc['scope'] = list(set(doc['scope']))
        return doc

    def createToken(self, user=None, days=None, scope=None, apiKey=None):
        """
        Creates a new token. You can create an anonymous token
        (such as for CSRF mitigation) by passing "None" for the user argument.

        :param user: The user to create the session for.
        :type user: dict
        :param days: The lifespan of the session in days. If not passed, uses
            the database setting for cookie lifetime.
        :type days: float or int
        :param scope: Scope or list of scopes this token applies to. By default,
            will create a user authentication token.
        :type scope: str or list of str
        :param apiKey: If this token is being created via an API key, pass it
           so that we can record the provenance for cleanup and auditing.
        :type apiKey: dict
        :returns: The token document that was created.
        """
        now = datetime.datetime.utcnow()
        days = days or self.model('setting').get(SettingKey.COOKIE_LIFETIME)

        if scope is None:
            scope = (TokenScope.USER_AUTH,)
        elif isinstance(scope, six.string_types):
            scope = (scope,)

        token = {
            '_id': genToken(),
            'created': now,
            'expires': now + datetime.timedelta(days=float(days)),
            'scope': scope
        }

        if user is None:
            # Since these tokens don't correspond to a user, we want to be
            # able to load them by their value without passing a user or
            # force=True, so we set it to public access. This is OK since tokens
            # are not exposed externally for listing, and the _id is the secure
            # token value.
            self.setPublic(token, True, save=False)
        else:
            token['userId'] = user['_id']
            self.setUserAccess(token, user=user, level=AccessType.ADMIN,
                               save=False)

        if apiKey is not None:
            token['apiKeyId'] = apiKey['_id']

        return self.save(token)

    def addScope(self, token, scope):
        """
        Add a scope to this token. If the token already has the scope, this is
        a no-op.
        """
        if 'scope' not in token:
            token['scope'] = []

        if scope not in token['scope']:
            token['scope'].append(scope)
            token = self.save(token)

        return token

    def getAllowedScopes(self, token):
        """
        Return the list of allowed scopes for a given token.
        """
        return token.get('scope', (TokenScope.USER_AUTH,))

    def hasScope(self, token, scope):
        """
        Test whether the given token has the given set of scopes. Use this
        rather than comparing manually, since this method is backward
        compatible with tokens that do not contain a scope field.

        :param token: The token object.
        :type token: dict
        :param scope: A scope or set of scopes that will be tested as a subset
            of the given token's allowed scopes.
        :type scope: str or list of str
        """
        if token is None:
            return False

        if scope is None:
            return True

        if isinstance(scope, six.string_types):
            scope = (scope,)
        return set(scope).issubset(set(self.getAllowedScopes(token)))

    def clearForApiKey(self, apiKey):
        """
        Delete all tokens corresponding to an API key.
        """
        for token in self.find({'apiKeyId': apiKey['_id']}):
            self.remove(token)
