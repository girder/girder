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

    pluginRoots = [os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'test_plugins'),
                   os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                'test_additional_plugins')]

    conf = config.getConfig()
    conf['plugins'] = {'plugin_directory': ':'.join(pluginRoots)}


def tearDownModule():
    base.stopServer()


class PluginUtilitiesTestCase(base.TestCase):

    def testGetPluginParentDir(self):
        # Test it chooses the first in the path
        # (since does_nothing is in both places)
        self.assertEqual(plugin_utilities.getPluginParentDir('does_nothing'),
                         os.path.join(
                             os.path.dirname(os.path.dirname(__file__)),
                             'test_plugins'))

        # Raise an exception if a non-existent dir is specified
        with self.assertRaisesRegexp(
                Exception,
                'Plugin directory some_nonexistent_plugin does not exist'):
            plugin_utilities.getPluginParentDir('some_nonexistent_plugin')

    def testGetPluginDir(self):
        # Test that plugin_install_path option takes first precedence
        conf = config.getConfig()
        conf['plugins']['plugin_install_path'] = 'use_this_plugin_dir'

        self.assertEqual(plugin_utilities.getPluginDir(),
                         'use_this_plugin_dir')

        try:
            shutil.rmtree('use_this_plugin_dir')
        except OSError:
            pass

        del conf['plugins']['plugin_install_path']
