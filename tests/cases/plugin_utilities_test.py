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

import os
import shutil

from .. import base
from girder.utility import config, plugin_utilities


def setUpModule():
    base.startServer()

    pluginRoot = [os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'test_plugins'),
                  os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'test_other_plugins')]

    conf = config.getConfig()
    conf['plugins'] = {'plugin_directory': ','.join(pluginRoot)}


def tearDownModule():
    base.stopServer()


class PluginUtilitiesTestCase(base.TestCase):

    def testGetPluginParentDir(self):
        # Test basic functionality when we know where a dir lives
        self.assertEqual(plugin_utilities.getPluginParentDir('test_plugin'),
                         'tests/test_other_plugins')

        # Raise an exception if a non-existent dir is specified
        with self.assertRaisesRegexp(
                Exception,
                'Plugin directory some_nonexistent_plugin does not exist'):
            plugin_utilities.getPluginParentDir('some_nonexistent_plugin')

        # Raise an exception if plugin dir exists in multiple places
        # by making the test_plugin exist in both plugin directories
        with self.assertRaisesRegexp(
                Exception,
                'Plugin directory test_plugin exists in multiple paths'):
            duplicatePluginDir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'test_plugins',
                'test_plugin')

            try:
                os.makedirs(duplicatePluginDir)
                plugin_utilities.getPluginParentDir('test_plugin')
            except OSError:
                pass

        try:
            shutil.rmtree(duplicatePluginDir)
        except OSError:
            pass
