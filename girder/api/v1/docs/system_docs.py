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

from ..api_docs import Describe

apis = []

apis.append({
    'path': '/system/version',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getVersion',
        'summary': 'Get the version information for this server.'
    }]
})

apis.append({
    'path': '/system/setting',
    'resource': 'setting',
    'operations': [{
        'httpMethod': 'GET',
        'nickname': 'getSetting',
        'summary': 'Get the value of a system setting.',
        'notes': 'Must be a system administrator to call this.',
        'parameters': [
            Describe.param('key', 'The key identifying this setting.')
            ],
        'errorResponses': [
            Describe.errorResponse(
                'You are not a system administrator.', 403)
            ]
        }, {
        'httpMethod': 'PUT',
        'nickname': 'setSetting',
        'responseClass': 'Setting',
        'summary': 'Set the value for a system setting.',
        'notes': 'Must be a system administrator to call this. If the string '
                 'passed is a valid JSON object, it will be parsed and stored '
                 'as an object.',
        'parameters': [
            Describe.param('key', 'The key identifying this setting.'),
            Describe.param('value', 'The value for this setting.')
            ],
        'errorResponses': [
            Describe.errorResponse(
                'You are not a system administrator.', 403)
            ]
        }, {
        'httpMethod': 'DELETE',
        'nickname': 'unsetSetting',
        'summary': 'Unset the value for a system setting.',
        'notes': 'Must be a system administrator to call this. This is used to'
                 ' explicitly restore a setting to its default value.',
        'parameters': [
            Describe.param('key', 'The key identifying the setting to unset.')
            ],
        'errorResponses': [
            Describe.errorResponse(
                'You are not a system administrator.', 403)
            ]
        }]
    })


Describe.declareApi('system', apis=apis)
