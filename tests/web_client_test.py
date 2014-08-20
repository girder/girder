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

from girder.constants import ROOT_DIR
from . import base


def setUpModule():
    os.environ['PORT'] = '50001'
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class WebClientTestCase(base.TestCase):
    def setUp(self):
        self.specFile = os.environ['SPEC_FILE']
        self.coverageFile = os.environ['COVERAGE_FILE']
        base.TestCase.setUp(self)

    def testWebClientSpec(self):

        cmd = (
            os.path.join(
                ROOT_DIR, 'node_modules', 'phantomjs', 'bin', 'phantomjs'),
            os.path.join(ROOT_DIR, 'clients', 'web', 'test', 'specRunner.js'),
            'http://localhost:50001/static/built/testEnv.html',
            self.specFile,
            self.coverageFile
        )

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT)

        (stdoutdata, stderrdata) = process.communicate()

        print(stdoutdata)

        self.assertEqual(process.returncode, 0)
