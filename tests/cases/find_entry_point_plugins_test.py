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
import unittest

from contextlib import contextmanager
from six import BytesIO

from girder.utility.plugin_utilities import findEntryPointPlugins, getPluginFailureInfo


class FakeEntryPoint(object):
    def __init__(self, name):
        self.name = name
        self.load = lambda: None


class FindEntryPointPluginsTestCase(unittest.TestCase):
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsNone(self, iter_entry_points):
        iter_entry_points.return_value = []

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertFalse(plugins)

    @mock.patch('pkg_resources.resource_exists')
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsNoConfig(self, iter_entry_points, resource_exists):
        iter_entry_points.return_value = [FakeEntryPoint(name='entry point plugin')]
        resource_exists.return_value = False

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertIn('entry point plugin', plugins)

    @mock.patch('pkg_resources.resource_stream')
    @mock.patch('pkg_resources.resource_exists')
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsJSONConfig(self, iter_entry_points, resource_exists,
                                            resource_stream):
        iter_entry_points.return_value = [FakeEntryPoint(name='entry_point_plugin_json')]

        # Load as JSON
        resource_exists.return_value = True

        @contextmanager
        def resource_stream_json_value():
            yield BytesIO(b'{"name": "Plugin name from JSON", "description": "Plugin description"}')

        resource_stream.return_value = resource_stream_json_value()

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertIn('entry_point_plugin_json', plugins)
        self.assertEqual(plugins['entry_point_plugin_json']['name'], 'Plugin name from JSON')
        self.assertEqual(plugins['entry_point_plugin_json']['description'], 'Plugin description')

    @mock.patch('pkg_resources.resource_stream')
    @mock.patch('pkg_resources.resource_exists')
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsBadJSONConfig(self, iter_entry_points, resource_exists,
                                               resource_stream):
        iter_entry_points.return_value = [FakeEntryPoint(name='entry_point_plugin_bad_json')]

        # Load as JSON
        resource_exists.return_value = True

        @contextmanager
        def resource_stream_json_value():
            yield BytesIO(b'{"name": "Plugin name from JSON", bad_json')

        resource_stream.return_value = resource_stream_json_value()

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertIn('entry_point_plugin_bad_json', plugins)

        failures = getPluginFailureInfo()
        self.assertIn('entry_point_plugin_bad_json', failures)
        self.assertIn('traceback', failures['entry_point_plugin_bad_json'])
        self.assertIn('ValueError', failures['entry_point_plugin_bad_json']['traceback'])

    @mock.patch('pkg_resources.resource_stream')
    @mock.patch('pkg_resources.resource_exists')
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsYAMLConfig(self, iter_entry_points, resource_exists,
                                            resource_stream):
        iter_entry_points.return_value = [FakeEntryPoint(name='entry_point_plugin_yaml')]

        # Load as YAML
        resource_exists.side_effect = [False, True]

        @contextmanager
        def resource_stream_yml_value():
            yield BytesIO(b'"name": "Plugin name from YAML"\n"description": "Plugin description"')

        resource_stream.return_value = resource_stream_yml_value()

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertIn('entry_point_plugin_yaml', plugins)
        self.assertEqual(plugins['entry_point_plugin_yaml']['name'], 'Plugin name from YAML')
        self.assertEqual(plugins['entry_point_plugin_yaml']['description'], 'Plugin description')

    @mock.patch('pkg_resources.resource_stream')
    @mock.patch('pkg_resources.resource_exists')
    @mock.patch('girder.utility.plugin_utilities.iter_entry_points')
    def testFindEntryPointPluginsBadYAMLConfig(self, iter_entry_points, resource_exists,
                                               resource_stream):
        iter_entry_points.return_value = [FakeEntryPoint(name='entry_point_plugin_bad_yaml')]

        # Load as YAML
        resource_exists.side_effect = [False, True]

        @contextmanager
        def resource_stream_yaml_value():
            yield BytesIO(b'"name": "Plugin name from YAML"\nbad_yaml\n}')

        resource_stream.return_value = resource_stream_yaml_value()

        plugins = {}
        findEntryPointPlugins(plugins)

        iter_entry_points.assert_called_once_with(group='girder.plugin')

        self.assertIn('entry_point_plugin_bad_yaml', plugins)

        failures = getPluginFailureInfo()
        self.assertIn('entry_point_plugin_bad_yaml', failures)
        self.assertIn('traceback', failures['entry_point_plugin_bad_yaml'])
        self.assertIn('ScannerError', failures['entry_point_plugin_bad_yaml']['traceback'])
