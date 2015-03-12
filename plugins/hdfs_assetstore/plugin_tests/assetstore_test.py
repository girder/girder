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

import os
import sys
import shutil

from girder.constants import AssetstoreType
from tests import base
from snakebite.client import Client
from snakebite.errors import FileNotFoundException


_mockRoot = os.path.join(os.path.dirname(__file__), 'mock_fs')


class MockSnakebiteClient(object):
    """
    We mock the whole snakebite client to simulate many types of interaction
    with an HDFS instance. This uses the `mock_fs` directory as the root of
    the mock filesystem for easy management of the test dataset.
    """
    def __init__(self, **kwargs):
        self.root = _mockRoot

    def _convertPath(self, path):
        if path[0] == '/':
            path = path[1:]

        return os.path.join(self.root, path)

    def serverdefaults(self):
        pass

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
            'port': 9000,
            'path': '/test'
        }

        resp = self.request(path='/assetstore', method='POST', params=params)
        self.assertStatus(resp, 401)

        self.assertFalse(os.path.isdir(os.path.join(_mockRoot, 'test')))
        resp = self.request(path='/assetstore', method='POST', params=params,
                            user=self.admin)
        self.assertTrue(os.path.isdir(os.path.join(_mockRoot, 'test')))
