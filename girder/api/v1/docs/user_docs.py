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

from ..api_docs import Describe

apis = []

apis.append({
    'path': '/user',
    'resource': 'user',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'findUsers',
        'responseClass': 'User',
        'summary': 'List or search for users.',
        'parameters': [
            Describe.param(
                'text', "Pass this to perform a full text search for items.",
                required=False),
            Describe.param(
                'limit', "Result set size limit (default=50).", required=False,
                dataType='int'),
            Describe.param(
                'offset', "Offset into result set (default=0).", required=False,
                dataType='int'),
            Describe.param(
                'sort', "Field to sort the user list by (default=lastName)",
                required=False),
            Describe.param(
                'sortdir', "1 for ascending, -1 for descending (default=1)",
                required=False, dataType='int')
            ]
        }, {
        'httpMethod': 'POST',
        'nickname': 'createUser',
        'responseClass': 'User',
        'summary': 'Create a new user.',
        'parameters': [
            Describe.param('login', "The user's requested login."),
            Describe.param('email', "The user's email address."),
            Describe.param('firstName', "The user's first name."),
            Describe.param('lastName', "The user's last name."),
            Describe.param('password', "The user's requested password")
            ],
        'errorResponses': [
            Describe.errorResponse(
                'A parameter was invalid, or the specified login or email '
                'already exists in the system.')
            ]
        }]
    })

apis.append({
    'path': '/user/login',
    'resource': 'user',
    'responseClass': 'Token',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'login',
        'returns': 'Authentication token',
        'summary': 'Log in to the system.',
        'notes': 'Returns a cookie that should be passed back in future '
                 'requests.',
        'parameters': [
            Describe.param('login', "Your email or login."),
            Describe.param('password', "Your password.")
            ],
        'errorResponses': [
            Describe.errorResponse('Missing parameter'),
            Describe.errorResponse('Invalid login or password.', 403)
            ]
        }]
    })

apis.append({
    'path': '/user/logout',
    'resource': 'user',
    'operations': [{
        'httpMethod': 'POST',
        'nickname': 'logout',
        'responseClass': 'Token',
        'summary': 'Log out of the system.',
        'notes': "Attempts to delete your authentication cookie."
        }]
    })

apis.append({
    'path': '/user/{userId}',
    'resource': 'user',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getUserById',
        'responseClass': 'User',
        'summary': 'Get a user by ID.',
        'parameters': [
            Describe.param('userId', 'The ID of the user.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse('You do not have permission to see this '
                                   'user.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'deleteUserById',
        'responseClass': 'User',
        'summary': 'Delete a user by ID.',
        'parameters': [
            Describe.param('userId', 'The ID of the user.', paramType='path')
            ],
        'errorResponses': [
            Describe.errorResponse('ID was invalid.'),
            Describe.errorResponse('You do not have permission to delete this '
                                   'user.', 403)
            ]
        }]
    })

Describe.declareApi('user', apis=apis)
