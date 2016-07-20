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
import six

from girder import config
from tests import base
from six import StringIO

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


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


def invokeCli(argv, username='', password='', useApiUrl=False):
    """
    Invoke the Girder Python client CLI with a set of arguments.
    """
    if useApiUrl:
        apiUrl = 'http://localhost:%s/api/v1' % os.environ['GIRDER_PORT']
        argsList = ['girder-client', '--api-url', apiUrl]
    else:
        argsList = ['girder-client', '--port', os.environ['GIRDER_PORT']]

    if username:
        argsList += ['--username', username]
    if password:
        argsList += ['--password', password]

    argsList += list(argv)

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
        self.publicFolder = six.next(self.model('folder').childFolders(
            parentType='user', parent=self.user, user=None, limit=1))
        self.apiKey = self.model('api_key').createApiKey(self.user, name='')

        self.downloadDir = os.path.join(
            os.path.dirname(__file__), '_testDownload')
        shutil.rmtree(self.downloadDir, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(self.downloadDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def testCliHelp(self):
        ret = invokeCli(())
        self.assertNotEqual(ret['exitVal'], 0)

        ret = invokeCli(('-h',))
        self.assertIn('usage: girder-cli', ret['stdout'])
        self.assertEqual(ret['exitVal'], 0)

    def testUploadDownload(self):
        localDir = os.path.join(os.path.dirname(__file__), 'testdata')
        args = ['upload', str(self.publicFolder['_id']), localDir]
        with self.assertRaises(girder_client.HttpError):
            invokeCli(args)

        with self.assertRaises(girder_client.HttpError):
            invokeCli(['--api-key', '1234'] + args)

        # Test dry-run and blacklist options
        ret = invokeCli(['--dryrun', '--blacklist=hello.txt'] + args,
                        username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn('Ignoring file hello.txt as it is blacklisted',
                      ret['stdout'])

        ret = invokeCli(args, username='mylogin', password='password',
                        useApiUrl=True)
        self.assertEqual(ret['exitVal'], 0)
        six.assertRegex(
            self, ret['stdout'],
            'Creating Folder from .*tests/cases/py_client/testdata')
        self.assertIn('Uploading Item from hello.txt', ret['stdout'])

        subfolder = six.next(self.model('folder').childFolders(
            parent=self.publicFolder, parentType='folder', limit=1))
        self.assertEqual(subfolder['name'], 'testdata')

        items = list(self.model('folder').childItems(folder=subfolder))

        toUpload = list(os.listdir(localDir))
        self.assertEqual(len(toUpload), len(items))

        downloadDir = os.path.join(os.path.dirname(localDir), '_testDownload')

        ret = invokeCli(('download', str(subfolder['_id']), downloadDir),
                        username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        for downloaded in os.listdir(downloadDir):
            if downloaded == '.girder_metadata':
                continue
            self.assertIn(downloaded, toUpload)

        # Download again to same location, we should not get errors
        ret = invokeCli(('download', str(subfolder['_id']), downloadDir),
                        username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)

        # Download again to same location, using path, we should not get errors
        ret = invokeCli(('download', '/user/mylogin/Public/testdata',
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)

        # Try uploading using API key
        ret = invokeCli(['--api-key', self.apiKey['key']] + args)
        self.assertEqual(ret['exitVal'], 0)
        six.assertRegex(
            self, ret['stdout'],
            'Creating Folder from .*tests/cases/py_client/testdata')
        self.assertIn('Uploading Item from hello.txt', ret['stdout'])

        # Test localsync, it shouldn't touch files on 2nd pass
        ret = invokeCli(('localsync', str(subfolder['_id']),
                         downloadDir), username='mylogin',
                        password='password')
        self.assertEqual(ret['exitVal'], 0)

        old_mtimes = {}
        for fname in os.listdir(downloadDir):
            filename = os.path.join(downloadDir, fname)
            old_mtimes[fname] = os.path.getmtime(filename)

        ret = invokeCli(('localsync', str(subfolder['_id']),
                         downloadDir), username='mylogin',
                        password='password')
        self.assertEqual(ret['exitVal'], 0)

        for fname in os.listdir(downloadDir):
            if fname == '.girder_metadata':
                continue
            filename = os.path.join(downloadDir, fname)
            self.assertEqual(os.path.getmtime(filename), old_mtimes[fname])

    def testLeafFoldersAsItems(self):
        localDir = os.path.join(os.path.dirname(__file__), 'testdata')
        args = ['upload', str(self.publicFolder['_id']), localDir,
                '--leaf-folders-as-items']

        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        six.assertRegex(
            self, ret['stdout'],
            'Creating Item from folder .*tests/cases/py_client/testdata')
        self.assertIn('Adding file world.txt', ret['stdout'])

        # Test re-use existing case
        args.append('--reuse')
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn('File hello.txt already exists in parent Item',
                      ret['stdout'])
