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

from ..describe import Description, autoDescribeRoute
from ..rest import Resource, filtermodel
from girder.exceptions import RestException
from girder.models.api_key import ApiKey as ApiKeyModel
from girder.models.setting import Setting
from girder.models.user import User
from girder.constants import AccessType, SettingKey
from girder.api import access


class ApiKey(Resource):
    def __init__(self):
        super(ApiKey, self).__init__()
        self.resourceName = 'api_key'
        self.route('GET', (), self.listKeys)
        self.route('POST', (), self.createKey)
        self.route('POST', ('token',), self.createToken)
        self.route('PUT', (':id',), self.updateKey)
        self.route('DELETE', (':id',), self.deleteKey)

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('List API keys for a given user.')
        .notes('Only site administrators may list keys for other users. If no '
               'userId parameter is passed, lists keys for the current user.')
        .param('userId', 'ID of the user whose keys to list.', required=False)
        .pagingParams(defaultSort='name')
        .errorResponse()
    )
    def listKeys(self, userId, limit, offset, sort):
        user = self.getCurrentUser()

        if userId not in {None, str(user['_id'])}:
            self.requireAdmin(user)
            user = User().load(userId, force=True, exc=True)

        return list(ApiKeyModel().list(user, offset=offset, limit=limit, sort=sort))

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('Create a new API key.')
        .param('name', 'Name for the API key.', required=False, default='', strip=True)
        .jsonParam('scope', 'JSON list of scopes for this key.', required=False)
        .param('tokenDuration', 'Max number of days tokens created with this '
               'key will last.', required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean', default=True)
        .errorResponse()
    )
    def createKey(self, name, scope, tokenDuration, active):
        if Setting().get(SettingKey.API_KEYS):
            return ApiKeyModel().createApiKey(
                user=self.getCurrentUser(), name=name, scope=scope, days=tokenDuration,
                active=active)
        else:
            raise RestException('API key functionality is disabled on this instance.')

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('Update an API key.')
        .modelParam('id', 'The ID of the API key.', model=ApiKeyModel, destName='apiKey',
                    level=AccessType.WRITE)
        .param('name', 'Name for the key.', required=False, strip=True)
        .jsonParam('scope', 'JSON list of scopes for this key.', required=False,
                   default=())
        .param('tokenDuration', 'Max number of days tokens created with this key will last.',
               required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean')
        .errorResponse()
    )
    def updateKey(self, apiKey, name, scope, tokenDuration, active):
        if active is not None:
            apiKey['active'] = active
        if name is not None:
            apiKey['name'] = name
        if tokenDuration is not None:
            apiKey['tokenDuration'] = tokenDuration
        if scope != ():
            apiKey['scope'] = scope

        return ApiKeyModel().save(apiKey)

    @access.user
    @autoDescribeRoute(
        Description('Delete an API key.')
        .modelParam('id', 'The ID of the API key to delete.', model=ApiKeyModel,
                    level=AccessType.ADMIN, destName='apiKey')
        .errorResponse()
    )
    def deleteKey(self, apiKey):
        ApiKeyModel().remove(apiKey)
        return {'message': 'Deleted API key %s.' % apiKey['name']}

    @access.public
    @autoDescribeRoute(
        Description('Create a token from an API key.')
        .param('key', 'The API key.', strip=True)
        .param('duration', 'Number of days that the token should last.',
               required=False, dataType='float')
        .errorResponse()
    )
    def createToken(self, key, duration):
        if not Setting().get(SettingKey.API_KEYS):
            raise RestException('API key functionality is disabled on this instance.')

        user, token = ApiKeyModel().createToken(key, days=duration)

        self.sendAuthTokenCookie(token=token, days=duration)

        # Return the same structure as a normal user login, except do not
        # include the full user document since the key may not authorize
        # reading user information.
        return {
            'user': {
                '_id': user['_id']
            },
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'scope': token['scope']
            }
        }
