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

from .. import base
from girder.utility import config


class CustomRootTestCase(base.TestCase):

    def setUp(self):
        pluginRoot = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                  'test_plugins')
        conf = config.getConfig()
        conf['plugins'] = {'plugin_directory': pluginRoot}
        base.enabledPlugins.append('test_plugin')

        base.startServer()

    def tearDown(self):
        base.stopServer()

    def testCustomWebRoot(self):
        """
        Tests the ability of plugins to serve their own custom server roots.
        """
        # Root (/) should serve our custom route
        resp = self.request('/', prefix='', isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.collapse_body(), 'hello world')

        # Normal web client should now be served from /girder
        resp = self.request('/girder', prefix='', isJson=False)
        self.assertStatusOk(resp)
        self.assertTrue('g-global-info-apiroot' in resp.collapse_body())

        # Api should be served out of /api/v1
        resp = self.request('/api/v1', prefix='', isJson=False)
        self.assertStatusOk(resp)
        self.assertTrue('Girder REST API Documentation' in resp.collapse_body())

        # /api should redirect to /api/v1
        resp = self.request('/api', prefix='', isJson=False)
        self.assertStatus(resp, 303)
        self.assertTrue('/api/v1' in resp.collapse_body())

        # Our custom API augmentations should still work
        resp = self.request('/describe')
        self.assertStatusOk(resp)
        self.assertTrue('apis' in resp.json)
        otherDocs = [x for x in resp.json['apis'] if x['path'] == '/other']
        self.assertEqual(len(otherDocs), 1)

        resp = self.request('/describe/other')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['apis']), 1)

        resp = self.request('/other')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, ['custom REST route'])

        # Api should not be served out of /girder/api/v1
        resp = self.request('/girder/api/v1', prefix='', isJson=False)
        self.assertStatus(resp, 404)

        # Test our staticFile method
        resp = self.request('/static_route', prefix='', isJson=False)
        self.assertEqual(resp.collapse_body(), 'Hello world!\n')
