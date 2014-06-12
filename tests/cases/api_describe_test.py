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

from .. import base

from girder.constants import AccessType, ROOT_DIR
from girder.api import describe


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ApiDescribeTestCase(base.TestCase):
    """
    Makes sure our swagger auto API docs are working.
    """

    def testApiDescribe(self):
        # Get coverage for serving the static swagger page
        resp = self.request(path='', method='GET', isJson=False)
        self.assertStatus(resp, 200)

        # Test top level describe endpoint
        resp = self.request(path='/describe', method='GET')
        self.assertStatus(resp, 200)
        self.assertTrue('/api/v1/describe' in resp.json['basePath'])
        self.assertEqual(resp.json['swaggerVersion'], describe.SWAGGER_VERSION)
        self.assertEqual(resp.json['apiVersion'], describe.API_VERSION)
        self.assertTrue({'path': '/group'} in resp.json['apis'])

        # Request a specific resource's description, sanity check
        resp = self.request(path='/describe/user', method='GET')
        self.assertStatus(resp, 200)
        for routeDoc in resp.json['apis']:
            self.assertHasKeys(('path', 'operations'), routeDoc)
            self.assertTrue(len(routeDoc['operations']) > 0)
