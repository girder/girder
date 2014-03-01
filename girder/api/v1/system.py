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
from .api_docs import API_VERSION
from .docs import system_docs
from ..rest import Resource, RestException


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """

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

    def getPlugins(self):
        """
        Return the plugin information for the system. This includes a list of
        all of the currently enabled plugins, as well as
        """
        self.requireAdmin(self.getCurrentUser())

        return {
            'all': plugin_utilities.findAllPlugins(),
            'enabled': self.model('setting').get(SettingKey.PLUGINS_ENABLED, ())
        }

    def enablePlugins(self, params):
        self.requireParams(('plugins',), params)
        self.requireAdmin(self.getCurrentUser())
        try:
            plugins = json.loads(params['plugins'])
        except ValueError:
            raise RestException('Plugins parameter should be a JSON list.')

        return self.model('setting').set(SettingKey.PLUGINS_ENABLED, plugins)

    @Resource.endpoint
    def DELETE(self, path, params):
        if not path:
            raise RestException('Unsupported operation.')
        elif path[0] == 'setting':
            self.requireParams(('key',), params)
            self.requireAdmin(self.getCurrentUser())
            return self.model('setting').unset(params['key'])
        else:
            raise RestException('Unsupported operation.')

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            raise RestException('Unsupported operation.')
        elif path[0] == 'version':
            return {'apiVersion': API_VERSION}
        elif path[0] == 'setting':
            self.requireParams(('key',), params)
            self.requireAdmin(self.getCurrentUser())
            return self.model('setting').get(params['key'])
        elif path[0] == 'plugins':
            return self.getPlugins()
        else:
            raise RestException('Unsupported operation.')

    @Resource.endpoint
    def PUT(self, path, params):
        if not path:
            raise RestException('Unsupported operation.')
        elif path[0] == 'setting':
            return self.setSetting(params)
        elif path[0] == 'plugins':
            return self.enablePlugins(params)
        else:
            raise RestException('Unsupported operation.')
