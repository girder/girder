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

import datetime

from .model_base import AccessControlledModel
from girder.constants import AccessType, SettingKey, TokenScope
from girder.exceptions import ValidationException
from girder.utility import genToken


class ApiKey(AccessControlledModel):
    """
    This model represents API keys corresponding to users.
    """
    def initialize(self):
        self.name = 'api_key'
        self.ensureIndices(('userId', 'key'))

        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'active', 'created', 'key', 'lastUse', 'name', 'scope',
            'tokenDuration', 'userId'
        })

    def validate(self, doc):
        from .token import Token
        from .user import User

        if doc['tokenDuration']:
            doc['tokenDuration'] = float(doc['tokenDuration'])
        else:
            doc['tokenDuration'] = None

        doc['name'] = doc['name'].strip()
        doc['active'] = bool(doc.get('active', True))

        if doc['scope'] is not None:
            if not isinstance(doc['scope'], (list, tuple)):
                raise ValidationException('Scope must be a list, or None.')
            if not doc['scope']:
                raise ValidationException('Custom scope list must not be empty.')

            # Ensure only registered scopes are being set
            admin = User().load(doc['userId'], force=True)['admin']
            scopes = TokenScope.scopeIds(admin)
            unknownScopes = set(doc['scope']) - scopes
            if unknownScopes:
                raise ValidationException('Invalid scopes: %s.' % ','.join(unknownScopes))

        # Deactivating an already existing token
        if '_id' in doc and not doc['active']:
            Token().clearForApiKey(doc)

        return doc

    def remove(self, doc):
        # Clear tokens corresponding to this API key.
        from .token import Token
        Token().clearForApiKey(doc)
        super(ApiKey, self).remove(doc)

    def list(self, user, limit=0, offset=0, sort=None):
        """
        List API keys for a given user.

        :param user: The user whose keys to list.
        :type user: dict
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :rtype: iterable of API keys for the user.
        """
        return self.find({
            'userId': user['_id']
        }, limit=limit, offset=offset, sort=sort)

    def createApiKey(self, user, name, scope=None, days=None, active=True):
        """
        Create a new API key for a user.

        :param user: The user who owns the API key.
        :type user: dict
        :param name: A human readable name for the API key
        :param days: The lifespan of the session in days. If not passed, uses
            the database setting for cookie lifetime. Note that this is a
            maximum duration; clients may request tokens with a shorter lifetime
            than this value.
        :type days: float or int
        :param scope: Scope or list of scopes this API key grants. By default,
            will grant tokens provided full access on behalf of the user.
        :type scope: str, list of str, or set of str
        :param active: Whether this key is active.
        :returns: The API key document that was created.
        """
        apiKey = {
            'created': datetime.datetime.utcnow(),
            'lastUse': None,
            'tokenDuration': days,
            'name': name,
            'scope': scope,
            'userId': user['_id'],
            'key': genToken(40),
            'active': active
        }

        return self.setUserAccess(apiKey, user, level=AccessType.ADMIN, save=True)

    def createToken(self, key, days=None):
        """
        Create a token using an API key.

        :param key: The API key (the key itself, not the full document).
        :type key: str
        :param days: You may request a token duration up to the token duration
            of the API key itself, or pass None to use the API key duration.
        :type days: float or None
        """
        from .setting import Setting
        from .token import Token
        from .user import User

        apiKey = self.findOne({
            'key': key
        })

        if apiKey is None or not apiKey['active']:
            raise ValidationException('Invalid API key.')

        cap = apiKey['tokenDuration'] or Setting().get(
            SettingKey.COOKIE_LIFETIME)
        days = min(float(days or cap), cap)

        user = User().load(apiKey['userId'], force=True)

        # Mark last used stamp
        apiKey['lastUse'] = datetime.datetime.utcnow()
        apiKey = self.save(apiKey)
        token = Token().createToken(user=user, days=days, scope=apiKey['scope'], apiKey=apiKey)
        return (user, token)
