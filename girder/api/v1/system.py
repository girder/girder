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
from ..describe import API_VERSION, Description
from ..rest import Resource, RestException


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """
    def __init__(self):
        self.resourceName = 'system'
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
        self.requireAdmin(self.getCurrentUser())

        if 'list' in params:
            try:
                settings = json.loads(params['list'])

                if type(settings) is not list:
                    raise ValueError()
            except ValueError:
                raise RestException('List was not a valid JSON list.')
        else:
            self.requireParams(('key', 'value'), params)
            settings = ({'key': params['key'], 'value': params['value']},)

        for setting in settings:
            if setting['value'] is None:
                value = None
            else:
                try:
                    value = json.loads(setting['value'])
                except ValueError:
                    value = setting['value']

            if value is None:
                self.model('setting').unset(key=setting['key'])
            else:
                self.model('setting').set(key=setting['key'], value=value)

        return True
    setSetting.description = (
        Description('Set the value for a system setting, or a list of them.')
        .notes("""Must be a system administrator to call this. If the value
               passed is a valid JSON object, it will be parsed and stored
               as an object.""")
        .param('key', 'The key identifying this setting.', required=False)
        .param('value', 'The value for this setting.', required=False)
        .param('list', 'A JSON list of objects with key and value representing '
               'a list of settings to set.', required=False)
        .errorResponse('You are not a system administrator.', 403))

    def getSetting(self, params):
        self.requireAdmin(self.getCurrentUser())

        getFuncName = 'get'
        funcParams = {}
        if 'default' in params:
            if params['default'] == 'none':
                funcParams['default'] = None
            elif params['default'] == 'default':
                getFuncName = 'getDefault'
            elif len(params['default']):
                raise RestException("Default was not 'none', 'default', or "
                                    "blank.")
        getFunc = getattr(self.model('setting'), getFuncName)
        if 'list' in params:
            try:
                keys = json.loads(params['list'])

                if type(keys) is not list:
                    raise ValueError()
            except ValueError:
                raise RestException('List was not a valid JSON list.')

            return {k: getFunc(k, **funcParams) for k in keys}
        else:
            self.requireParams('key', params)
            return getFunc(params['key'], **funcParams)
    getSetting.description = (
        Description('Get the value of a system setting, or a list of them.')
        .notes('Must be a system administrator to call this.')
        .param('key', 'The key identifying this setting.', required=False)
        .param('list', 'A JSON list of keys representing a set of settings to'
               ' return.', required=False)
        .param('default', 'If "none", return a null value if a setting is '
               'currently the default value.  If "default", return the '
               'default value of the setting(s).', required=False)
        .errorResponse('You are not a system administrator.', 403))

    def getPlugins(self, params):
        """
        Return the plugin information for the system. This includes a list of
        all of the currently enabled plugins, as well as
        """
        self.requireAdmin(self.getCurrentUser())

        return {
            'all': plugin_utilities.findAllPlugins(),
            'enabled': self.model('setting').get(SettingKey.PLUGINS_ENABLED)
        }
    getPlugins.description = (
        Description('Get the lists of all available and all enabled plugins.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403))

    def getVersion(self, params):
        return {'apiVersion': API_VERSION}
    getVersion.description = Description(
        'Get the version information for this server.')

    def enablePlugins(self, params):
        self.requireParams('plugins', params)
        self.requireAdmin(self.getCurrentUser())
        try:
            plugins = json.loads(params['plugins'])
        except ValueError:
            raise RestException('Plugins parameter should be a JSON list.')

        return self.model('setting').set(SettingKey.PLUGINS_ENABLED, plugins)
    enablePlugins.description = (
        Description('Set the list of enabled plugins for the system.')
        .responseClass('Setting')
        .notes('Must be a system administrator to call this.')
        .param('plugins', 'JSON array of plugins to enable.')
        .errorResponse('You are not a system administrator.', 403))

    def unsetSetting(self, params):
        self.requireParams('key', params)
        self.requireAdmin(self.getCurrentUser())
        return self.model('setting').unset(params['key'])
    unsetSetting.description = (
        Description('Unset the value for a system setting.')
        .notes("""Must be a system administrator to call this. This is used to
               explicitly restore a setting to its default value.""")
        .param('key', 'The key identifying the setting to unset.')
        .errorResponse('You are not a system administrator.', 403))
