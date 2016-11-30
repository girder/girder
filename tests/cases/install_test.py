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
from girder.utility import install

pluginRoot = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_plugins')


class PluginOpts():
    def __init__(self, plugin=None, force=False, symlink=False, dev=False, npm='npm',
                 skip_requirements=False, all_plugins=False, plugins=None, watch=False,
                 watch_plugin=None):
        self.plugin = plugin
        self.force = force
        self.symlink = symlink
        self.development = dev
        self.npm = npm
        self.skip_requirements = skip_requirements
        self.all_plugins = all_plugins
        self.plugins = plugins
        self.watch = watch
        self.watch_plugin = watch_plugin


class ProcMock(object):
    def __init__(self, rc=0, keyboardInterrupt=False):
        self.returncode = rc
        self.kbi = keyboardInterrupt

    def communicate(self):
        return (None, None)

    def wait(self):
        if self.kbi:
            raise KeyboardInterrupt()


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

        self.mockPluginDir(self.pluginDir)

    def tearDown(self):
        base.TestCase.tearDown(self)

        self.unmockPluginDir()
        shutil.rmtree(self.baseDir)

    def testInstallPlugin(self):
        install.install_plugin(PluginOpts(plugin=[
            os.path.join(pluginRoot, 'has_deps'),
            os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
        ]))

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
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(pluginRoot, 'has_deps')
        ]))

        # Test skip_requirements
        install.install_plugin(PluginOpts(
            force=True, skip_requirements=True,
            plugin=[os.path.join(pluginRoot, 'has_deps')]))

        # If bad path is given, should fail gracefuly
        with six.assertRaisesRegex(self, Exception, 'Invalid plugin directory'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                '/bad/install/path'
            ]))

        # If src == dest, we should still run npm and succeed.
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(self.pluginDir, 'has_deps')
        ]))

        # Should fail if exists as directory and symlink is true
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_deps')
            ], symlink=True))

        # Should be a link if force=True and symlink=True
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
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(pluginRoot, 'has_deps')
        ]))

        self.assertFalse(os.path.islink(os.path.join(
            self.pluginDir, 'has_deps')))

    def testDevDependencies(self):
        install.install_plugin(PluginOpts(plugin=[
            os.path.join(pluginRoot, 'has_dev_deps'),
            os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
        ]))

        self.assertTrue(os.path.exists(
            os.path.join(self.pluginDir, 'has_dev_deps', 'plugin.json')))

        install.install_plugin(PluginOpts(plugin=[
            os.path.join(pluginRoot, 'has_dev_deps'),
            os.path.join(constants.ROOT_DIR, 'plugins', 'jobs')
        ], force=True, dev=True))

    def testGruntDependencies(self):
        install.install_plugin(PluginOpts(plugin=[
            os.path.join(pluginRoot, 'has_grunt_deps')
        ]))

        self.assertTrue(os.path.exists(
            os.path.join(self.pluginDir, 'has_grunt_deps', 'plugin.json')))

        # Should fail if exists and force=False
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

        # Should succeed if force=True
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(pluginRoot, 'has_grunt_deps')
        ]))

        # If bad path is given, should fail gracefuly
        with six.assertRaisesRegex(self, Exception, 'Invalid plugin directory'):
            install.install_plugin(PluginOpts(force=True, plugin=[
                '/bad/install/path'
            ]))

        # If src == dest, we should still run npm and succeed.
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(self.pluginDir, 'has_grunt_deps')
        ]))

        # Should fail if exists as directory and symlink is true
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ], symlink=True))

        # Should be a link if force=True and symlink=True
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(pluginRoot, 'has_grunt_deps')
        ], symlink=True))

        self.assertTrue(os.path.islink(os.path.join(self.pluginDir, 'has_grunt_deps')))

        # Should fail if exists as link and symlink is false
        with six.assertRaisesRegex(self, Exception, 'Plugin already exists'):
            install.install_plugin(PluginOpts(plugin=[
                os.path.join(pluginRoot, 'has_grunt_deps')
            ]))

        # Should not be a link if force=True and symlink=False
        install.install_plugin(PluginOpts(force=True, plugin=[
            os.path.join(pluginRoot, 'has_grunt_deps')
        ]))

        self.assertFalse(os.path.islink(os.path.join(self.pluginDir, 'has_grunt_deps')))

    def testWebInstall(self):
        with mock.patch('subprocess.Popen', return_value=ProcMock(rc=2)) as p,\
                six.assertRaisesRegex(self, Exception, 'npm install .* returned 2'):
            install.install_web()

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(p.mock_calls[0][1][0][:2], ('npm', 'install'))
            self.assertEqual(p.mock_calls[0][2]['cwd'], constants.PACKAGE_DIR)

        with mock.patch('subprocess.Popen', return_value=ProcMock()):
            install.install_web()

        with mock.patch('subprocess.Popen', return_value=ProcMock()) as p:
            install.install_web()
            self.assertNotIn('--production', p.mock_calls[0][1][0])

        with mock.patch('subprocess.Popen', return_value=ProcMock()) as p:
            install.install_web(PluginOpts(dev=True))

            self.assertNotIn('--production', p.mock_calls[0][1][0])

        # Test initiation of web install via the REST API
        user = self.model('user').createUser(
            login='admin', firstName='admin', lastName='admin', email='a@foo.com',
            password='passwd', admin=True)

        with mock.patch('subprocess.Popen', return_value=ProcMock()) as p:
            # Test without progress
            resp = self.request('/system/web_build', method='POST', user=user)
            self.assertStatusOk(resp)

            self.assertEqual(len(p.mock_calls), 2)
            self.assertEqual(
                list(p.mock_calls[0][1][0]), ['npm', 'install', '--unsafe-perm'])
            self.assertEqual(
                list(p.mock_calls[1][1][0]),
                ['npm', 'run', 'build', '--',
                 '--no-progress=true', '--env=prod', '--plugins='])

        # Test with progress (requires actually calling a subprocess)
        os.environ['PATH'] = '%s:%s' % (
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'mockpath'),
            os.environ.get('PATH', '')
        )
        resp = self.request('/system/web_build', method='POST', user=user, params={
            'progress': True
        })
        self.assertStatusOk(resp)

        # Test watch commands
        with mock.patch('subprocess.Popen', return_value=ProcMock()) as p:
            install.install_web(PluginOpts(watch=True))

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(list(p.mock_calls[0][1][0]), ['npm', 'run', 'watch'])

        with mock.patch('subprocess.Popen', return_value=ProcMock()) as p:
            install.install_web(PluginOpts(watch_plugin='jobs'))

            self.assertEqual(len(p.mock_calls), 1)
            self.assertEqual(
                list(p.mock_calls[0][1][0]),
                ['npm', 'run', 'watch', '--', '--all-plugins', 'webpack:plugin_jobs']
            )

        # Keyboard interrupt should be handled gracefully
        with mock.patch('subprocess.Popen', return_value=ProcMock(keyboardInterrupt=True)):
            install.install_web(PluginOpts(watch=True))
