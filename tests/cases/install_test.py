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

import tempfile
import shutil
import os
import tarfile

from .. import base
from girder.utility import install, config

pluginRoot = os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    'test_plugins'
)


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

        # Create temporary directories for testing installations
        self.baseDir = tempfile.mkdtemp()

        self.pluginDir = os.path.join(self.baseDir, 'plugin')
        os.mkdir(self.pluginDir)

        # dump some plugins into tarballs
        self.singlePluginTarball = os.path.join(self.baseDir, 'single.tgz')
        t = tarfile.TarFile(
            name=self.singlePluginTarball,
            mode='w'
        )
        t.add(os.path.join(pluginRoot, 'has_deps'), arcname='single')
        t.close()

        self.combinedPluginTarball = os.path.join(self.baseDir, 'multi.tgz')
        t = tarfile.TarFile(
            name=self.combinedPluginTarball,
            mode='w'
        )
        t.add(os.path.join(pluginRoot, 'has_deps'), arcname='multi1')
        t.add(os.path.join(pluginRoot, 'has_deps'), arcname='multi2')
        t.close()

        # set the plugin path
        conf = config.getConfig()
        conf['plugins'] = {'plugin_directory': self.pluginDir}

    def tearDown(self):
        base.TestCase.tearDown(self)

        del config.getConfig()['plugins']
        shutil.rmtree(self.baseDir)

    def testSinglePluginInstallFromTgz(self):
        self.assertEqual(
            install.install_plugin(self.singlePluginTarball),
            ['single']
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.pluginDir, 'single', 'plugin.json')
            )
        )

        # make sure it fails when force is off
        self.assertEqual(
            install.install_plugin(self.singlePluginTarball),
            []
        )

        # make sure it succeeds when force is on
        self.assertEqual(
            install.install_plugin(self.singlePluginTarball, force=True),
            ['single']
        )

    def testSinglePluginInstallFromDir(self):
        l = install.install_plugin(
            os.path.join(pluginRoot, 'has_deps')
        )
        self.assertEqual(l, ['has_deps'])
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.pluginDir, 'has_deps', 'plugin.json')
            )
        )

    def testMultiPluginInstallFromTgz(self):
        self.assertEqual(
            sorted(install.install_plugin(self.combinedPluginTarball)),
            ['multi1', 'multi2']
        )
        self.assertTrue(
            os.path.isfile(
                os.path.join(self.pluginDir, 'multi1', 'plugin.json')
            )
        )

        # make sure it fails when force is off
        self.assertEqual(
            install.install_plugin(self.combinedPluginTarball),
            []
        )

        # make sure it succeeds when force is on
        self.assertEqual(
            sorted(install.install_plugin(
                self.combinedPluginTarball,
                force=True
            )),
            ['multi1', 'multi2']
        )

    def testInvalidClientInstall(self):
        self.assertFalse(
            install.install_web('http://notvalid.kitware.com')
        )
        self.assertFalse(
            install.install_web(
                os.path.join(
                    pluginRoot, 'has_deps', 'plugin.json'
                )
            )
        )
