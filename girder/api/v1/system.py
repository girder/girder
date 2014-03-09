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

import json

from girder.utility import plugin_utilities
from girder.constants import SettingKey
from .. import describe
from ..docs import API_VERSION
from ..rest import Resource, RestException


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """
    def __init__(self):
        self.route('DELETE', ('setting',), self.unsetSetting)
        self.route('GET', ('version',), self.getVersion)
        self.route('GET', ('setting',), self.getSetting)
        self.route('GET', ('plugins',), self.getPlugins)
        self.route('PUT', ('setting',), self.setSetting)
        self.route('PUT', ('plugins',), self.enablePlugins)

    def setSetting(self, params):
        """
        Set a system-wide setting. Validation of the setting is performed in
        the setting model. If the setting is a valid JSON string, it will be
        passed to the model as the corresponding dict, otherwise it is simply
        passed as a raw string.
        """
        self.requireParams(('key', 'value'), params)
        self.requireAdmin(self.getCurrentUser())

        try:
            value = json.loads(params['value'])
        except ValueError:
            value = params['value']

        return self.model('setting').set(key=params['key'], value=value)
    setSetting.description = {
        'summary': 'Set the value for a system setting.',
        'notes': 'Must be a system administrator to call this. If the string '
                 'passed is a valid JSON object, it will be parsed and stored '
                 'as an object.',
        'parameters': [
            describe.param('key', 'The key identifying this setting.'),
            describe.param('value', 'The value for this setting.')
        ],
        'errorResponses': [
            describe.errorResponse(
                'You are not a system administrator.', 403)
        ]
    }

    def getSetting(self, params):
        self.requireParams(('key',), params)
        self.requireAdmin(self.getCurrentUser())
        return self.model('setting').get(params['key'])
    getSetting.description = {
        'summary': 'Get the value of a system setting.',
        'notes': 'Must be a system administrator to call this.',
        'parameters': [
            describe.param('key', 'The key identifying this setting.')
        ],
        'errorResponses': [
            describe.errorResponse(
                'You are not a system administrator.', 403)
        ]
    }

    def getPlugins(self, params):
        """
        Return the plugin information for the system. This includes a list of
        all of the currently enabled plugins, as well as
        """
        self.requireAdmin(self.getCurrentUser())

        return {
            'all': plugin_utilities.findAllPlugins(),
            'enabled': self.model('setting').get(SettingKey.PLUGINS_ENABLED, ())
        }
    getPlugins.description = {
        'summary': 'Get the lists of all available and all enabled plugins.',
        'notes': 'Must be a system administrator to call this.',
        'errorResponses': [
            describe.errorResponse(
                'You are not a system administrator.', 403)
        ]
    }

    def getVersion(self, params):
        return {'apiVersion': API_VERSION}
    getVersion.description = {
        'summary': 'Get the version information for this server.'
    }

    def enablePlugins(self, params):
        self.requireParams(('plugins',), params)
        self.requireAdmin(self.getCurrentUser())
        try:
            plugins = json.loads(params['plugins'])
        except ValueError:
            raise RestException('Plugins parameter should be a JSON list.')

        return self.model('setting').set(SettingKey.PLUGINS_ENABLED, plugins)
    enablePlugins.description = {
        'responseClass': 'Setting',
        'summary': 'Set the list of enabled plugins for the system.',
        'notes': 'Must be a system administrator to call this.',
        'parameters': [
            describe.param('plugins', 'JSON array of plugins to enable.')
        ],
        'errorResponses': [
            describe.errorResponse(
                'You are not a system administrator.', 403)
        ]
    }

    def unsetSetting(self, params):
        self.requireParams(('key',), params)
        self.requireAdmin(self.getCurrentUser())
        return self.model('setting').unset(params['key'])
    unsetSetting.description = {
        'summary': 'Unset the value for a system setting.',
        'notes': 'Must be a system administrator to call this. This is used to'
                 ' explicitly restore a setting to its default value.',
        'parameters': [
            describe.param('key', 'The key identifying the setting to unset.')
        ],
        'errorResponses': [
            describe.errorResponse(
                'You are not a system administrator.', 403)
        ]
    }
