#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import os
import types

from .. import base


class ApiPrefixTestCase(base.TestCase):

    def setUp(self):
        self.mockPluginDir(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_plugins'))
        base.enabledPlugins.append('has_api_prefix')

        base.startServer()

        from girder.plugins import has_api_prefix
        self.assertIsInstance(has_api_prefix, types.ModuleType)

    def tearDown(self):
        base.stopServer()
        self.unmockPluginDir()
        base.dropAllTestDatabases()

    def testCustomWebRoot(self):
        """
        Tests the ability of plugins to serve their own custom server roots.
        """
        # Root (/) should serve our custom route
        resp = self.request('/prefix/resourceful')
        self.assertStatusOk(resp)

        self.assertEqual(resp.json, ['custom REST route'])
