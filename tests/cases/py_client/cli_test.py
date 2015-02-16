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

import contextlib
import girder_client.cli
import mock
import os
import sys

# Need to set the environment variable before importing girder
os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')  # noqa

from tests import base
from StringIO import StringIO

@contextlib.contextmanager
def captureOutput():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


class SysExitException(Exception):
    pass


def invokeCli(argv, username, password):
    """
    Invoke the girder python client CLI with a set of arguments.
    """
    argsList = ['girder-client', '--port', os.environ['GIRDER_PORT'],
                '--username', username, '--password', password]  + list(argv)
    exitVal = 0
    with mock.patch.object(sys, 'argv', argsList),\
            mock.patch('sys.exit', side_effect=SysExitException) as exit,\
            captureOutput() as output:
        try:
            girder_client.cli.main()
        except SysExitException:
            args = exit.mock_calls[0][1]
            exitVal = args[0] if len(args) else 0
    return {
        'exitVal': exitVal,
        'stdout': output[0],
        'stderr': output[1]
    }


def setUpModule():
    plugins = os.environ.get('ENABLED_PLUGINS', '')
    if plugins:
        base.enabledPlugins.extend(plugins.split())
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class PythonCliTestCase(base.TestCase):

    def testCliUpload(self):
        self.model('user').createUser(firstName='First', lastName='Last',
            login='mylogin', password='mypassword', email='a@abc.com')
        print invokeCli((), username='mylogin', password='mypassword')['stderr']
