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
import os

from .. import base
from girder.api.rest import endpoint
from girder.utility import config


def setUpModule():
    pluginRoot = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              'test_plugins')
    conf = config.getConfig()
    conf['plugins'] = {'plugin_directory': pluginRoot}
    base.enabledPlugins = ['test_plugin']

    base.startServer()


def tearDownModule():
    base.stopServer()


class TestEndpointDecoratorException(base.TestCase):
    """Tests the endpoint decorator exception handling."""

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

        resp = self.request('/collection/unbound/default/noargs', params={
            'val': False
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, True)

        resp = self.request('/collection/unbound/default', params={
            'val': False
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, True)

        resp = self.request('/collection/unbound/explicit')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            'name': 'collection',
            'user': None
        })

    def testRawResponse(self):
        resp = self.request('/other/rawWithDecorator', isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), 'this is a raw response')

        resp = self.request('/other/rawInternal', isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), 'this is also a raw response')
