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
import shutil
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


def invokeCli(argv, username='', password=''):
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

    def setUp(self):
        base.TestCase.setUp(self)

        self.user = self.model('user').createUser(
            firstName='First', lastName='Last', login='mylogin',
            password='password', email='email@email.com')

        self.downloadDir = os.path.join(
            os.path.dirname(__file__), '_testDownload')
        shutil.rmtree(self.downloadDir, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(self.downloadDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def testCliHelp(self):
        ret = invokeCli(())
        self.assertIn('error: too few arguments', ret['stderr'])
        self.assertNotEqual(ret['exitVal'], 0)

        ret = invokeCli(('-h',))
        self.assertIn('usage: girder-client', ret['stdout'])
        self.assertEqual(ret['exitVal'], 0)

    def testUploadDownload(self):
        publicFolder = self.model('folder').childFolders(
            parentType='user', parent=self.user, user=None).next()

        localDir = os.path.dirname(__file__)
        args = ('-c', 'upload', str(publicFolder['_id']), localDir)
        flag = False
        try:
            invokeCli(args)
        except girder_client.AuthenticationError:
            flag = True

        self.assertTrue(flag)

        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn(
            'Creating Folder from tests/cases/py_client', ret['stdout'])
        self.assertIn('Uploading Item from cli_test.py', ret['stdout'])

        subfolder = self.model('folder').childFolders(
            parent=publicFolder, parentType='folder').next()
        self.assertEqual(subfolder['name'], 'py_client')

        items = list(self.model('folder').childItems(folder=subfolder))

        toUpload = list(os.listdir(localDir))
        self.assertEqual(len(toUpload), len(items))

        downloadDir = os.path.join(localDir, '_testDownload')

        ret = invokeCli(('-c', 'download', str(subfolder['_id']), downloadDir),
                        username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        for downloaded in os.listdir(downloadDir):
            self.assertIn(downloaded, toUpload)
