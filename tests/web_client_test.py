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

import os
import subprocess
import sys

# Need to set the environment variable before importing girder
os.environ['GIRDER_PORT'] = '50001'

from girder.constants import ROOT_DIR, SettingKey
from . import base


def setUpModule():
    mockS3 = False
    if 's3' in os.environ['ASSETSTORE_TYPE']:
        mockS3 = True
    plugins = os.environ.get('ENABLED_PLUGINS', '')
    if plugins:
        base.enabledPlugins.extend(plugins.split())
    base.startServer(False, mockS3=mockS3)


def tearDownModule():
    base.stopServer()


class WebClientTestCase(base.TestCase):
    def setUp(self):
        self.specFile = os.environ['SPEC_FILE']
        self.coverageFile = os.environ['COVERAGE_FILE']
        assetstoreType = os.environ['ASSETSTORE_TYPE']
        self.webSecurity = os.environ.get('WEB_SECURITY', 'true')
        if self.webSecurity != 'false':
            self.webSecurity = 'true'
        base.TestCase.setUp(self, assetstoreType)
        # One of the web client tests uses this db, so make sure it is cleared
        # ahead of time
        base.dropGridFSDatabase('girder_webclient_gridfs')
        plugins = os.environ.get('ENABLED_PLUGINS', '')
        if plugins:
            self.model('setting').set(SettingKey.PLUGINS_ENABLED,
                                      plugins.split())

    def testWebClientSpec(self):

        cmd = (
            os.path.join(
                ROOT_DIR, 'node_modules', 'phantomjs', 'bin', 'phantomjs'),
            '--web-security=%s' % self.webSecurity,
            os.path.join(ROOT_DIR, 'clients', 'web', 'test', 'specRunner.js'),
            'http://localhost:50001/static/built/testEnv.html',
            self.specFile,
            self.coverageFile
        )

        returncode = subprocess.call(cmd, stdout=sys.stdout.fileno(),
                                     stderr=sys.stdout.fileno())
        self.assertEqual(returncode, 0)
