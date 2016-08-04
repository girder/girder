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
import six
import shutil
import tempfile

from .. import base
from girder import constants
from girder.utility import install, config

pluginRoot = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                          'test_plugins')

POPEN = 'subprocess.Popen'


class PluginOpts():
    def __init__(self, plugin=None, force=False, symlink=False, dev=False, npm='npm',
                 skip_requirements=False, skip_web_client=False):
        self.plugin = plugin
        self.force = force
        self.symlink = symlink
        self.development = dev
        self.npm = npm
        self.skip_requirements = skip_requirements
        self.skip_web_client = skip_web_client


class ProcMock(object):
    def __init__(self, rc=0):
        self.returncode = rc

    def communicate(self):
        return (None, None)


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class InstallTestCase(base.TestCase):
    """
    Test installing resources and plugins using the install module.
    """

    def setUp(self):
        base.TestCase.setUp(self)

        self.baseDir = tempfile.mkdtemp()
        self.pluginDir = os.path.join(self.baseDir, 'plugins')
        os.mkdir(self.pluginDir)

        conf = config.getConfig()
        conf['plugins'] = {'plugin_directory': self.pluginDir}

    def tearDown(self):
        base.TestCase.tearDown(self)

        del config.getConfig()['plugins']
        shutil.rmtree(self.baseDir)

    def testInstallPlugin(self):
        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_deps'),
                os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
            ]))

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(p.mock_calls[0][1][0][:2], ('npm', 'install'))
            self.assertEqual(p.mock_calls[0][2]['cwd'], constants.PACKAGE_DIR)

            self.assertTrue(os.path.exists(
                os.path.join(self.pluginDir, 'jobs', 'plugin.yml')))
            self.assertTrue(os.path.exists(
                os.path.join(self.pluginDir, 'has_deps', 'plugin.json')))

        # Should fail if exists and force=False
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ]))

        # Should succeed if force=True
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ]))

        # If npm install returns 1, should fail
        with mock.patch(POPEN, return_value=ProcMock(rc=1)), \
                six.assertRaisesRegex(self, Exception, 'npm install returned 1'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ]))

        # Using skip_web_client and skip_requirements should circumvent install steps
        with mock.patch(POPEN, return_value=ProcMock(rc=1)) as mockPopen:
            install.install_plugin(PluginOpts(
                force=True, skip_requirements=True, skip_web_client=True,
                plugin=[os.path.join(pluginRoot, 'has_deps')]))

            self.assertEqual(len(mockPopen.mock_calls), 0)

        # If bad path is given, should fail gracefuly
        with six.assertRaisesRegex(self, Exception, 'Invalid plugin directory'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                '/bad/install/path'
            ]))

        # If src == dest, we should still run npm and succeed.
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(self.pluginDir, 'has_deps')
            ]))

        # Should fail if exists as directory and symlink is true
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ], symlink=True))

        # Should be a link if force=True and symlink=True
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ], symlink=True))

            self.assertTrue(os.path.islink(os.path.join(
                self.pluginDir, 'has_deps')))

            # Should fail if exists as link and symlink is false
            with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
                install.install_plugin(PluginOpts(plugin=[
                    os.path.join(pluginRoot, 'has_deps')
                ]))

        # Should not be a link if force=True and symlink=False
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ]))

            self.assertFalse(os.path.islink(os.path.join(
                self.pluginDir, 'has_deps')))

    def testDevDependencies(self):
        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_dev_deps'),
                os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
            ]))

            self.assertTrue(os.path.exists(
                os.path.join(self.pluginDir, 'has_dev_deps', 'plugin.json')))
            self.assertTrue('--production' in p.mock_calls[0][1][0])

        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_dev_deps'),
                os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
            ], force=True, dev=True))

            self.assertTrue('--production' not in p.mock_calls[0][1][0])

    def testGruntDependencies(self):
        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(p.mock_calls[0][1][0][:2], ('npm', 'install'))
            self.assertEqual(p.mock_calls[0][2]['cwd'], constants.PACKAGE_DIR)

            self.assertTrue(os.path.exists(
                os.path.join(self.pluginDir, 'has_grunt_deps', 'plugin.json')))

        # Should fail if exists and force=False
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

        # Should succeed if force=True
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

        # If npm install returns 1, should fail
        with mock.patch(POPEN, return_value=ProcMock(rc=1)), \
                six.assertRaisesRegex(self, Exception, 'npm install returned 1'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

        # If bad path is given, should fail gracefuly
        with six.assertRaisesRegex(self, Exception, 'Invalid plugin directory'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                '/bad/install/path'
            ]))

        # If src == dest, we should still run npm and succeed.
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(self.pluginDir, 'has_grunt_deps')
            ]))

        # Should fail if exists as directory and symlink is true
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ], symlink=True))

        # Should be a link if force=True and symlink=True
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ], symlink=True))

            self.assertTrue(os.path.islink(os.path.join(
                self.pluginDir, 'has_grunt_deps')))

            # Should fail if exists as link and symlink is false
            with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
                install.install_plugin(PluginOpts(plugin=[
                    os.path.join(pluginRoot, 'has_grunt_deps')
                ]))

        # Should not be a link if force=True and symlink=False
        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_plugin(PluginOpts(force=True, plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

            self.assertFalse(os.path.islink(os.path.join(
                self.pluginDir, 'has_grunt_deps')))

    def testWebInstall(self):
        with mock.patch(POPEN, return_value=ProcMock(rc=2)) as p,\
                six.assertRaisesRegex(self, Exception, 'npm install returned 2'):
            install.install_web()

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(p.mock_calls[0][1][0][:2], ('npm', 'install'))
            self.assertEqual(p.mock_calls[0][2]['cwd'], constants.PACKAGE_DIR)

        with mock.patch(POPEN, return_value=ProcMock()):
            install.install_web()

        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_web()
            self.assertTrue('--production' in p.mock_calls[0][1][0])

        with mock.patch(POPEN, return_value=ProcMock()) as p:
            install.install_web(PluginOpts(dev=True))

            self.assertTrue('--production' not in p.mock_calls[0][1][0])
