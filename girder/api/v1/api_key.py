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

from ..describe import Description, describeRoute
from ..rest import Resource, RestException, filtermodel, loadmodel
from girder.constants import AccessType
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
    @filtermodel('api_key')
    @describeRoute(
        Description('List API keys for a given user.')
        .notes('Only site administrators may list keys for other users. If no '
               'userId parameter is passed, lists keys for the current user.')
        .param('userId', 'ID of the user whose keys to list.', required=False)
        .pagingParams(defaultSort='name')
        .errorResponse()
    )
    def listKeys(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()

        if 'userId' in params and params['userId'] != str(user['_id']):
            self.requireAdmin(user)
            user = self.model('user').load(
                params['userId'], force=True, exc=True)

        return list(self.model('api_key').list(
            user, offset=offset, limit=limit, sort=sort))

    @access.user
    @filtermodel('api_key')
    @describeRoute(
        Description('Create a new API key.')
        .param('name', 'Name for the API key.', required=False)
        .param('scope', 'JSON list of scopes for this key.', required=False)
        .param('tokenDuration', 'Max number of days tokens created with this '
               'key will last.', required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean', default=True)
        .errorResponse()
    )
    def createKey(self, params):
        name = params.get('name', '').strip()
        days = params.get('tokenDuration')
        active = self.boolParam('active', params, True)

        if 'scope' in params:
            try:
                scope = json.loads(params['scope'])
            except ValueError:
                raise RestException(
                    'The "scope" parameter must be a JSON list.')
        else:
            scope = None

        return self.model('api_key').createApiKey(
            user=self.getCurrentUser(), name=name, scope=scope, days=days,
            active=active)

    @access.user
    @loadmodel(map={'id': 'apiKey'}, model='api_key', level=AccessType.WRITE)
    @filtermodel('api_key')
    @describeRoute(
        Description('Update an API key.')
        .param('id', 'The ID of the API key.', paramType='path')
        .param('name', 'Name for the key.', required=False)
        .param('scope', 'JSON list of scopes for this key.', required=False)
        .param('tokenDuration', 'Max number of days tokens created with this '
               'key will last.', required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean', default=True)
        .errorResponse()
    )
    def updateKey(self, apiKey, params):
        apiKey['active'] = self.boolParam('active', params, apiKey['active'])
        apiKey['name'] = params.get('name', apiKey['name']).strip()
        apiKey['tokenDuration'] = params.get(
            'tokenDuration', apiKey['tokenDuration'])

        if 'scope' in params:
            try:
                apiKey['scope'] = json.loads(params['scope'])
            except ValueError:
                raise RestException(
                    'The "scope" parameter must be a JSON list.')

        return self.model('api_key').save(apiKey)

    @access.user
    @loadmodel(map={'id': 'apiKey'}, model='api_key', level=AccessType.ADMIN)
    @describeRoute(
        Description('Delete an API key.')
        .param('id', 'The ID of the API key to delete.', paramType='path')
        .errorResponse()
    )
    def deleteKey(self, apiKey, params):
        self.model('api_key').remove(apiKey)
        return {'message': 'Deleted API key %s.' % apiKey['name']}

    @access.public
    @describeRoute(
        Description('Create a token from an API key.')
        .param('key', 'The API key.')
        .param('duration', 'Number of days that the token should last.',
               required=False, dataType='float')
        .errorResponse()
    )
    def createToken(self, params):
        self.requireParams('key', params)

        key = params['key'].strip()
        days = params.get('duration')

        user, token = self.model('api_key').createToken(key, days=days)

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
