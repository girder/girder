# -*- coding: utf-8 -*-
import contextlib
import girder_client.cli
from http.client import HTTPConnection
import io
import logging
import os
import requests
import shutil
import sys
import urllib.parse
import httmock
import unittest.mock

from girder import config
from girder.models.api_key import ApiKey
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from girder_client.cli import GirderCli
from tests import base

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


@contextlib.contextmanager
def captureOutput():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [io.StringIO(), io.StringIO()]
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
    with unittest.mock.patch.object(sys, 'argv', argsList),\
            unittest.mock.patch('sys.exit', side_effect=SysExitException) as exit,\
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
        super().setUp()

        self.user = User().createUser(
            firstName='First', lastName='Last', login='mylogin',
            password='password', email='email@girder.test')
        self.publicFolder = next(Folder().childFolders(
            parentType='user', parent=self.user, user=None, limit=1))
        self.apiKey = ApiKey().createApiKey(self.user, name='')

        self.downloadDir = os.path.join(
            os.path.dirname(__file__), '_testDownload')
        shutil.rmtree(self.downloadDir, ignore_errors=True)

    def tearDown(self):
        logger = logging.getLogger('girder_client')
        logger.setLevel(logging.ERROR)
        logger.handlers = []
        shutil.rmtree(self.downloadDir, ignore_errors=True)

        base.TestCase.tearDown(self)

    def testUrlByPart(self):
        # This test does NOT connect to the test server. It only checks that the
        # client object has the expected attributes.

        username = None
        password = None

        for case in [
            # Check that apiUrl is preferred
            {
                'input': {'apiUrl': 'https://girder.example.com:74/api/v74',
                          'host': 'foo', 'scheme': 'bar', 'port': 42, 'apiRoot': 'bar'},
                'expected': {
                    'urlBase': 'https://girder.example.com:74/api/v74/',
                    'host': None, 'scheme': None, 'port': None}
            },
            # Check different configuration of URL by part
            {
                'input': {},
                'expected': {
                    'urlBase': 'http://localhost:8080/api/v1/',
                    'host': 'localhost', 'scheme': 'http', 'port': 8080}
            },
            {
                'input': {'host': 'localhost'},
                'expected': {
                    'urlBase': 'http://localhost:8080/api/v1/',
                    'host': 'localhost', 'scheme': 'http', 'port': 8080}
            },
            {
                'input': {'port': 42},
                'expected': {
                    'urlBase': 'http://localhost:42/api/v1/',
                    'host': 'localhost', 'scheme': 'http', 'port': 42}
            },
            {
                'input': {'scheme': 'https'},
                'expected': {
                    'urlBase': 'https://localhost:443/api/v1/',
                    'host': 'localhost', 'scheme': 'https', 'port': 443}
            },
            {
                'input': {'host': 'girder.example.com'},
                'expected': {
                    'urlBase': 'https://girder.example.com:443/api/v1/',
                    'host': 'girder.example.com', 'scheme': 'https', 'port': 443}
            },
            {
                'input': {'host': 'girder.example.com', 'scheme': 'http'},
                'expected': {
                    'urlBase': 'http://girder.example.com:80/api/v1/',
                    'host': 'girder.example.com', 'scheme': 'http', 'port': 80}
            },
            {
                'input': {'host': 'localhost', 'port': 42},
                'expected': {
                    'urlBase': 'http://localhost:42/api/v1/',
                    'host': 'localhost', 'scheme': 'http', 'port': 42}
            },
            {
                'input': {'host': 'girder.example.com', 'port': 42},
                'expected': {
                    'urlBase': 'https://girder.example.com:42/api/v1/',
                    'host': 'girder.example.com', 'scheme': 'https', 'port': 42}
            },
            {
                'input': {'host': 'localhost', 'scheme': 'https'},
                'expected': {
                    'urlBase': 'https://localhost:443/api/v1/',
                    'host': 'localhost', 'scheme': 'https', 'port': 443}
            },
            {
                'input': {'host': 'girder.example.com', 'scheme': 'https'},
                'expected': {
                    'urlBase': 'https://girder.example.com:443/api/v1/',
                    'host': 'girder.example.com', 'scheme': 'https', 'port': 443}
            },

        ]:
            client = girder_client.cli.GirderCli(username, password, **case['input'])
            for attribute, value in case['expected'].items():
                self.assertEqual(getattr(client, attribute), value)

    def testCliHelp(self):
        ret = invokeCli(())
        self.assertNotEqual(ret['exitVal'], 0)

        ret = invokeCli(('-h',))
        self.assertIn('Usage: ', ret['stdout'])
        self.assertEqual(ret['exitVal'], 0)

    def testUploadDownload(self):
        localDir = os.path.join(os.path.dirname(__file__), 'testdata')
        args = ['upload', str(self.publicFolder['_id']), localDir, '--parent-type=folder']
        with self.assertRaises(requests.HTTPError):
            invokeCli(args)

        with self.assertRaises(requests.HTTPError):
            invokeCli(['--api-key', '1234'] + args)

        # Test dry-run and blacklist options
        ret = invokeCli(
            args + ['--dry-run', '--blacklist=hello.txt'], username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn('Ignoring file hello.txt as it is blacklisted', ret['stdout'])

        # Test with multiple files in a dry-run
        ret = invokeCli([
            'upload', str(self.publicFolder['_id']), '--parent-type=folder',
            os.path.join(localDir, 'hello.txt'),
            os.path.join(localDir, 'world.txt'), '--dry-run'],
            username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn('Uploading Item from hello.txt', ret['stdout'])
        self.assertIn('Uploading Item from world.txt', ret['stdout'])

        # Actually upload the test data
        ret = invokeCli(args, username='mylogin', password='password', useApiUrl=True)
        self.assertEqual(ret['exitVal'], 0)
        self.assertRegex(
            ret['stdout'], 'Creating Folder from .*tests/cases/py_client/testdata')
        self.assertIn('Uploading Item from hello.txt', ret['stdout'])

        subfolder = next(Folder().childFolders(
            parent=self.publicFolder, parentType='folder', limit=1))
        self.assertEqual(subfolder['name'], 'testdata')

        items = list(Folder().childItems(folder=subfolder))

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

        # Test uploading with reference
        queryList = []

        @httmock.urlmatch(netloc='localhost', path='/api/v1/file$', method='POST')
        def checkParams(url, request):
            # Add query for every file upload request
            queryList.append(urllib.parse.parse_qs(url[3]))

        with httmock.HTTMock(checkParams):
            ret = invokeCli(
                args + ['--reference', 'reference_string'], username='mylogin', password='password')

        # Test if reference is sent with each file upload
        fileList = os.listdir(localDir)
        self.assertTrue(queryList)
        self.assertTrue(fileList)
        self.assertEqual(len(queryList), len(fileList))
        for query in queryList:
            self.assertIn('reference', query)
            self.assertIn('reference_string', query['reference'])

        # Create a collection and subfolder
        resp = self.request('/collection', 'POST', user=self.user, params={
            'name': 'my_collection'
        })
        self.assertStatusOk(resp)
        resp = self.request('/folder', 'POST', user=self.user, params={
            'parentType': 'collection',
            'parentId': resp.json['_id'],
            'name': 'my_folder'
        })
        self.assertStatusOk(resp)

        # Test download of the collection
        ret = invokeCli(('download', '--parent-type=collection', '/collection/my_collection',
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(os.path.isdir(os.path.join(downloadDir, 'my_folder')))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of the collection auto-detecting parent-type
        ret = invokeCli(('download', '/collection/my_collection',
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(os.path.isdir(os.path.join(downloadDir, 'my_folder')))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of a user
        ret = invokeCli(('download', '--parent-type=user', '/user/mylogin',
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(
            os.path.isfile(os.path.join(downloadDir, 'Public', 'testdata', 'hello.txt')))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of a user auto-detecting parent-type
        ret = invokeCli(('download', '/user/mylogin',
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(
            os.path.isfile(os.path.join(downloadDir, 'Public', 'testdata', 'hello.txt')))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of an item
        items = list(Folder().childItems(folder=subfolder))
        item_id = items[0]['_id']
        item_name = items[0]['name']
        ret = invokeCli(('download', '--parent-type=item', '%s' % item_id,
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(
            os.path.isfile(os.path.join(downloadDir, item_name)))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of a file
        os.makedirs(downloadDir)
        items = list(Folder().childItems(folder=subfolder))
        file_name, file_doc = next(Item().fileList(items[0], data=False))

        ret = invokeCli(
            ('download', '--parent-type=file', '%s' % file_doc['_id'],
             os.path.join(downloadDir, file_name)),
            username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(
            os.path.isfile(os.path.join(downloadDir, file_name)))
        shutil.rmtree(downloadDir, ignore_errors=True)

        # Test download of an item auto-detecting parent-type
        ret = invokeCli(('download', '%s' % item_id,
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertTrue(
            os.path.isfile(os.path.join(downloadDir, item_name)))
        shutil.rmtree(downloadDir, ignore_errors=True)

        def _check_upload(ret):
            self.assertEqual(ret['exitVal'], 0)
            self.assertRegex(
                ret['stdout'],
                'Creating Folder from .*tests/cases/py_client/testdata')
            self.assertIn('Uploading Item from hello.txt', ret['stdout'])

        # Try uploading using API key
        _check_upload(invokeCli(['--api-key', self.apiKey['key']] + args))

        # Try uploading using API key set with GIRDER_API_KEY env. variable
        os.environ['GIRDER_API_KEY'] = self.apiKey['key']
        _check_upload(invokeCli(args))
        del os.environ['GIRDER_API_KEY']

        # Test localsync, it shouldn't touch files on 2nd pass
        ret = invokeCli(('localsync', str(subfolder['_id']),
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)

        old_mtimes = {}
        for fname in os.listdir(downloadDir):
            filename = os.path.join(downloadDir, fname)
            old_mtimes[fname] = os.path.getmtime(filename)

        ret = invokeCli(('localsync', str(subfolder['_id']),
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)

        for fname in os.listdir(downloadDir):
            if fname == '.girder_metadata':
                continue
            filename = os.path.join(downloadDir, fname)
            self.assertEqual(os.path.getmtime(filename), old_mtimes[fname])

        # Check that localsync command do not show '--parent-type' option help
        ret = invokeCli(('localsync', '--help'))
        self.assertNotIn('--parent-type', ret['stdout'])
        self.assertEqual(ret['exitVal'], 0)

        # Check that localsync command still accepts '--parent-type' argument
        ret = invokeCli(('localsync', '--parent-type', 'folder', str(subfolder['_id']),
                         downloadDir), username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)

    def testLeafFoldersAsItems(self):
        localDir = os.path.join(os.path.dirname(__file__), 'testdata')
        args = ['upload', str(self.publicFolder['_id']), localDir, '--leaf-folders-as-items']

        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertRegex(
            ret['stdout'], 'Creating Item from folder .*tests/cases/py_client/testdata')
        self.assertIn('Adding file world.txt', ret['stdout'])

        # Test re-use existing case
        args.append('--reuse')
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertIn('File hello.txt already exists in parent Item', ret['stdout'])

    def testVerboseLoggingLevel0(self):
        args = ['localsync', '--help']
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertEqual(logging.getLogger('girder_client').level, logging.ERROR)

    def testVerboseLoggingLevel1(self):
        args = ['-v', 'localsync', '--help']
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertEqual(logging.getLogger('girder_client').level, logging.WARNING)

    def testVerboseLoggingLevel2(self):
        args = ['-vv', 'localsync', '--help']
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertEqual(logging.getLogger('girder_client').level, logging.INFO)

    def testVerboseLoggingLevel3(self):
        args = ['-vvv', 'localsync', '--help']
        ret = invokeCli(args, username='mylogin', password='password')
        self.assertEqual(ret['exitVal'], 0)
        self.assertEqual(logging.getLogger('girder_client').level, logging.DEBUG)
        self.assertEqual(HTTPConnection.debuglevel, 1)

    def testRetryUpload(self):
        gc = GirderCli('mylogin', 'password',
                       host='localhost', port=os.environ['GIRDER_PORT'],
                       retries=5)

        def checkRetryHandler(*args, **kwargs):
            session = gc._session
            self.assertIsNotNone(session)
            self.assertIn(gc.urlBase, session.adapters)
            adapter = session.adapters[gc.urlBase]
            self.assertEqual(adapter.max_retries.total, 5)

        with unittest.mock.patch('girder_client.cli.GirderClient.sendRestRequest',
                                 side_effect=checkRetryHandler) as m:
            gc.sendRestRequest('')

        self.assertTrue(m.called)
