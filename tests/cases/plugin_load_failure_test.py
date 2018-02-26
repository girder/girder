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

import mock
import os

from .. import base
from girder.utility import plugin_utilities


class PluginLoadFailureTestCase(base.TestCase):
    """
    Test error reporting when a plugin fails to load.
    """

    def setUp(self):
        testPluginPath = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'test_plugins'
        ))
        self.mockPluginDir(testPluginPath)
        base.enabledPlugins.append('bad_server')

        with mock.patch('girder.utility.plugin_utilities.logprint.exception'):
            base.startServer()

    def tearDown(self):
        base.stopServer()
        self.unmockPluginDir()

    def testPluginLoadFailure(self):
        failureInfo = plugin_utilities.getPluginFailureInfo()
        self.assertIn('bad_server', failureInfo)
        self.assertIn('traceback', failureInfo['bad_server'])
        self.assertIn('Traceback', failureInfo['bad_server']['traceback'])
        self.assertIn('Exception: Bad server', failureInfo['bad_server']['traceback'])
