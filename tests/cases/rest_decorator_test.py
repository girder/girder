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

import json
import mock
import os
import requests

from .. import base
from girder import config
from girder.api.rest import endpoint
from girder.models.user import User


def setUpModule():
    os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
    config.loadConfig()
    testPluginPath = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'test_plugins'
    ))
    base.mockPluginDir(testPluginPath)
    base.enabledPlugins = ['test_plugin']

    with mock.patch('girder.utility.plugin_utilities.logprint.exception'):
        base.startServer(mock=False)


def tearDownModule():
    base.stopServer()


class TestEndpointDecoratorException(base.TestCase):
    """Tests the endpoint decorator exception handling."""

    def setUp(self):
        with mock.patch('girder.utility.plugin_utilities.logprint.exception'):
            super(TestEndpointDecoratorException, self).setUp()

    @endpoint
    def pointlessEndpointAscii(self, path, params):
        raise Exception('You did something wrong.')

    @endpoint
    def pointlessEndpointUnicode(self, path, params):
        raise Exception(u'\u0400 cannot be converted to ascii.')

    @endpoint
    def pointlessEndpointBytes(self, path, params):
        raise Exception('\x80\x80 cannot be converted to unicode or ascii.')

    def testEndpointExceptionAscii(self):
        resp = self.pointlessEndpointAscii('', {}).decode()
        obj = json.loads(resp)
        self.assertEqual(obj['type'], 'internal')

    def testEndpointExceptionUnicode(self):
        resp = self.pointlessEndpointUnicode('', {}).decode('utf8')
        obj = json.loads(resp)
        self.assertEqual(obj['type'], 'internal')

    def testEndpointExceptionBytes(self):
        resp = self.pointlessEndpointBytes('', {}).decode('utf8')
        obj = json.loads(resp)
        self.assertEqual(obj['type'], 'internal')

    def testBoundHandlerDecorator(self):
        user = User().createUser('tester', 'password', 'Test', 'User', 'test@test.com')

        resp = self.request('/collection/unbound/default/noargs', user=user, params={
            'val': False
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, True)

        resp = self.request('/collection/unbound/default', user=user, params={
            'val': False
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, True)

        resp = self.request('/collection/unbound/explicit', user=user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            'name': 'collection',
            'userLogin': 'tester'
        })

    def testRawResponse(self):
        resp = self.request('/other/rawWithDecorator', isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), 'this is a raw response')

        resp = self.request('/other/rawInternal', isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), 'this is also a raw response')

        # We must make an actual request in order to test response encoding
        # at the WSGI server layer.
        resp = requests.get(
            'http://127.0.0.1:%s/api/v1/other/rawReturningText' % os.environ['GIRDER_TEST_PORT'])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers['Content-Type'], 'text/plain;charset=utf-8')
        self.assertEqual(resp.content, b'this is not encoded \xf0\x9f\x91\x8d')
        self.assertEqual(resp.text, u'this is not encoded \U0001F44D')
