#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import httmock
import os
import shutil
import six
import sys

from girder.constants import AssetstoreType
from tests import base
from snakebite.client import Client  # noqa
from snakebite.errors import FileNotFoundException


_mockRoot = os.path.join(os.path.dirname(__file__), 'mock_fs')


def _long(val):
    return long(val) if six.PY2 else val  # noqa


class MockSnakebiteClient(object):
    """
    We mock the whole snakebite client to simulate many types of interaction
    with an HDFS instance. This uses the `mock_fs` directory as the root of
    the mock filesystem for easy management of the test dataset.
    """
    def __init__(self, port=None, **kwargs):
        self.root = _mockRoot
        self.port = port
        self.chunkSize = kwargs.get('chunkSize', 3)

    def _convertPath(self, path):
        if path[0] == '/':
            path = path[1:]

        return os.path.join(self.root, path)

    def serverdefaults(self):
        if self.port != 9000:
            raise Exception('Failed to connect to HDFS.')

    def df(self):
        return {
            'used': _long(100),
            'capacity': _long(1000)
        }

    def test(self, path, exists=False, directory=False, **kwargs):
        path = self._convertPath(path)
        if directory:
            return os.path.isdir(path)
        if exists:
            return os.path.exists(path)
        if os.path.exists(path):
            return True
        else:
            raise FileNotFoundException

    def mkdir(self, paths, create_parent=False, **kwargs):
        for path in paths:
            absPath = self._convertPath(path)
            if create_parent:
                os.makedirs(absPath)
            else:
                os.mkdir(absPath)
            yield {
                'path': path,
                'result': True
            }

    def ls(self, paths, **kwargs):
        for path in paths:
            absPath = self._convertPath(path)
            if not os.path.exists(absPath):
                raise FileNotFoundException('Not found: ' + absPath)
            elif os.path.isfile(absPath):
                yield {
                    'file_type': 'f',
                    'length': _long(os.stat(absPath).st_size),
                    'path': path
                }
            else:
                for i in os.listdir(absPath):
                    itemPath = os.path.join(absPath, i)
                    if os.path.isfile(itemPath):
                        yield {
                            'file_type': 'f',
                            'length': _long(os.stat(itemPath).st_size),
                            'path': os.path.join(path, i)
                        }
                    else:
                        yield {
                            'file_type': 'd',
                            'length': _long(0),
                            'path': os.path.join(path, i)
                        }

    def cat(self, paths, **kwargs):
        for path in paths:
            def stream():
                with open(self._convertPath(path), 'rb') as f:
                    while True:
                        data = f.read(self.chunkSize)
                        if not data:
                            break
                        yield data
            yield stream()

    def touchz(self, paths, **kwargs):
        for path in paths:
            absPath = self._convertPath(path)
            with open(absPath, 'a'):
                os.utime(absPath, None)
                yield {
                    'path': path,
                    'result': True
                }

    def stat(self, paths):
        # The weirdness of this method signature vs. return value reflects
        # the weirdness of the actual version in the snakebite client.
        for path in paths:
            absPath = self._convertPath(path)
            if os.path.isfile(absPath):
                return {
                    'file_type': 'f',
                    'length': _long(os.stat(absPath).st_size),
                    'path': path
                }
            elif os.path.isdir(absPath):
                return {
                    'file_type': 'd',
                    'length': _long(0),
                    'path': path
                }
            else:
                raise Exception('Not found: ' + path)

    def delete(self, paths, **kwargs):
        for path in paths:
            os.unlink(self._convertPath(path))
            yield {
                'path': path,
                'result': True
            }


# This seems to be the most straightforward way to mock the object globally
# such that it is also mocked in the request context. mock.patch was not
# sufficient in my initial experiments.
sys.modules['snakebite.client'].Client = MockSnakebiteClient


def setUpModule():
    base.enabledPlugins.append('hdfs_assetstore')
    base.startServer()


def tearDownModule():
    base.stopServer()


class HdfsAssetstoreTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.admin = self.model('user').createUser(
            email='admin@mail.com',
            login='admin',
            firstName='first',
            lastName='last',
            password='password',
            admin=True
        )

        shutil.rmtree(os.path.join(_mockRoot, 'test'), ignore_errors=True)

    def testAssetstore(self):
        params = {
            'type': AssetstoreType.HDFS,
            'name': 'test assetstore',
            'host': 'localhost',
            'port': 'bad value',
            'path': '/test'
        }

        # Make sure admin access required
        resp = self.request(path='/assetstore', method='POST', params=params)
        self.assertStatus(resp, 401)

        # Test assetstore validation
        resp = self.request(path='/assetstore', method='POST', params=params,
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['field'], 'port')

        params['port'] = 9000

        # Create the assetstore
        self.assertFalse(os.path.isdir(os.path.join(_mockRoot, 'test')))
        resp = self.request(path='/assetstore', method='POST', params=params,
                            user=self.admin)
        self.assertTrue(os.path.isdir(os.path.join(_mockRoot, 'test')))
        self.assertStatusOk(resp)
        assetstore = resp.json

        # Test updating of the assetstore
        resp = self.request(
            path='/assetstore/' + str(assetstore['_id']), method='PUT',
            user=self.admin, params={
                'name': 'test assetstore',
                'hdfsHost': 'localhost',
                'hdfsPath': '/test',
                'hdfsPort': 9001,
                'current': True
            })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Could not connect to HDFS at localhost:9001.')

        resp = self.request(
            path='/assetstore/' + str(assetstore['_id']), method='PUT',
            user=self.admin, params={
                'name': 'test update',
                'hdfsHost': 'localhost',
                'hdfsPath': '/test',
                'hdfsPort': 9000,
                'current': True
            })
        self.assertStatusOk(resp)

        # Test the capacity info
        resp = self.request(path='/assetstore/' + str(assetstore['_id']),
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['capacity'], {
            'free': 900,
            'total': 1000
        })

        path = '/hdfs_assetstore/%s/import' % assetstore['_id']
        params = {
            'progress': 'true',
            'parentType': 'user',
            'parentId': self.admin['_id'],
            'path': 'bad path'
        }

        # Make sure only admins can import
        resp = self.request(path=path, method='PUT', params=params)
        self.assertStatus(resp, 401)

        # Test importing a nonexistent path
        resp = self.request(path=path, method='PUT', params=params,
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'File not found: bad path.')

        params['path'] = '/'

        # Import a hierarchy into the admin user's root dir
        resp = self.request(path=path, method='PUT', params=params,
                            user=self.admin)
        self.assertStatusOk(resp)
        folders = list(self.model('folder').childFolders(
            parentType='user', parent=self.admin, user=self.admin))

        # Make sure the hierarchy got imported
        folder = None
        for folder in folders:
            if folder['name'] == 'to_import':
                break
        self.assertTrue(folder is not None)

        items = list(self.model('folder').childItems(
            folder=folder, user=self.admin))
        self.assertEqual(len(items), 2)

        for item in items:
            if item['name'] == 'hello.txt':
                helloItem = item
            elif item['name'] == 'world.txt':
                pass
            else:
                raise Exception('Unexpected item name: ' + item['name'])

        file = self.model('item').childFiles(
            item=helloItem, user=self.admin).next()

        # Download the file
        resp = self.request(path='/file/%s/download' % file['_id'],
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.collapse_body().strip(), 'hello')

        # Test download with range header
        resp = self.request(path='/file/%s/download' % file['_id'],
                            user=self.admin, isJson=False,
                            additionalHeaders=[('Range', 'bytes=1-3')])
        self.assertStatus(resp, 206)
        self.assertEqual('ell', self.getBody(resp))
        self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
        self.assertEqual(resp.headers['Content-Length'], 3)
        self.assertEqual(resp.headers['Content-Range'], 'bytes 1-3/6')

        # Test download with range header with skipped chunk
        resp = self.request(path='/file/%s/download' % file['_id'],
                            user=self.admin, isJson=False,
                            additionalHeaders=[('Range', 'bytes=4-')])
        self.assertStatus(resp, 206)
        self.assertEqual('o\n', self.getBody(resp))
        self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
        self.assertEqual(resp.headers['Content-Length'], 2)
        self.assertEqual(resp.headers['Content-Range'], 'bytes 4-5/6')

        helloTxtPath = os.path.join(_mockRoot, 'to_import', 'hello.txt')

        # Deleting an imported file should not delete the backing HDFS file
        self.assertTrue(os.path.isfile(helloTxtPath))
        resp = self.request(path='/file/' + str(file['_id']), method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(None, self.model('file').load(file['_id']))
        self.assertTrue(os.path.isfile(helloTxtPath))

        chunk1, chunk2 = ('test', 'upload')
        # Init upload
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'item',
                'parentId': helloItem['_id'],
                'name': 'testUpload.txt',
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)
        upload = resp.json
        absPath = os.path.join(
            _mockRoot, assetstore['hdfs']['path'][1:],
            upload['hdfs']['path'])

        # Temp file should be created
        self.assertEqual(upload['assetstoreId'], str(assetstore['_id']))
        self.assertFalse(upload['hdfs'].get('imported', False))
        self.assertTrue(os.path.isfile(absPath))

        # Test uploading to this assetstore
        @httmock.all_requests
        def webHdfsMock(url, request):
            if '50070' in url.netloc:
                # First request, we must issue a redirect to data node
                return {
                    'status_code': 307,
                    'headers': {
                        'Location': 'http://localhost:50075/foo'
                    }
                }
            elif url.netloc == 'localhost:50075':
                # Write the contents
                with open(absPath, 'a') as f:
                    f.write(request.body.read())
                return {
                    'status_code': 200
                }
            else:
                raise Exception('Unexpected request: ' + repr(url))

        with httmock.HTTMock(webHdfsMock):
            # Upload first chunk
            fields = [('offset', 0), ('uploadId', upload['_id'])]
            files = [('chunk', 'testUpload.txt', chunk1)]
            resp = self.multipartRequest(
                path='/file/chunk', user=self.admin, fields=fields, files=files)
            self.assertStatusOk(resp)

            # Get the offset (simulating resume)
            upload = resp.json
            self.assertEqual(upload['received'], len(chunk1))
            resp = self.request('/file/offset', user=self.admin, params={
                'uploadId': upload['_id']
            })
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['offset'], len(chunk1))

            fields = [('offset', len(chunk1)), ('uploadId', upload['_id'])]
            files = [('chunk', 'testUpload.txt', chunk2)]
            resp = self.multipartRequest(
                path='/file/chunk', user=self.admin, fields=fields, files=files)
            self.assertStatusOk(resp)
            file = resp.json

        # Download the file
        resp = self.request('/file/%s/download' % file['_id'],
                            isJson=False, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.collapse_body(), chunk1 + chunk2)

        # Delete the file, should remove the underlying file on disk
        resp = self.request('/file/' + str(file['_id']), method='DELETE',
                            user=self.admin)
        self.assertEqual(None, self.model('file').load(file['_id']))
        self.assertFalse(os.path.exists(absPath))
