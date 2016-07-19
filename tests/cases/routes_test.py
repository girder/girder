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

from .. import base
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException
from girder.constants import SettingKey, SettingDefault

testServer = None


def setUpModule():
    global testServer
    testServer = base.startServer()


def tearDownModule():
    base.stopServer()


class DummyResource(Resource):
    def __init__(self):
        super(DummyResource, self).__init__()
        self.route('GET', (':wc1', 'literal1'), self.handler)
        self.route('GET', (':wc1', 'literal2'), self.handler)
        self.route('GET', (':wc1', ':wc2'), self.handler)
        self.route('GET', (':wc1', 'literal1'), self.handler)
        self.route('GET', ('literal1', 'literal2'), self.handler)
        self.route('GET', (':wc1', 'admin'), self.handler)
        self.route('PATCH', (':id', 'patchy'), self.handler)
        self.route('GET', ('test', ), self.handler)
        self.route('PUT', ('test', ), self.handler)
        self.route('POST', ('test', ), self.handler)
        self.route('DELETE', ('test', ), self.handler)
        self.route('PATCH', ('test', ), self.handler)

    @access.public
    @describeRoute(
        Description('Dummy handler.')
    )
    def handler(self, **kwargs):
        return kwargs
    # We want to test adding and removing documentation when we add and remove
    # routes.


class RoutesTestCase(base.TestCase):
    """
    Unit tests of the routing system of REST Resources.
    """
    def testRouteSystem(self):
        dummy = DummyResource()

        # Bad route should give a useful exception.
        exc = None
        try:
            dummy.handleRoute('GET', (), {})
        except RestException as e:
            exc = e.message
        self.assertEqual(exc, 'No matching route for "GET "')

        # Make sure route ordering is correct; literals before wildcard tokens
        r = dummy.handleRoute('GET', ('literal1', 'foo'), {})
        self.assertEqual(r, {'wc1': 'literal1', 'wc2': 'foo', 'params': {}})

        r = dummy.handleRoute('GET', ('literal1', 'literal2'), {})
        self.assertEqual(r, {'params': {}})

        r = dummy.handleRoute('PATCH', ('guid', 'patchy'), {})
        self.assertEqual(r, {'id': 'guid', 'params': {}})

        # Add a new route with a new method
        dummy.route('DUMMY', (':id', 'dummy'), dummy.handler)
        r = dummy.handleRoute('DUMMY', ('guid', 'dummy'), {})
        self.assertEqual(r, {'id': 'guid', 'params': {}})
        # Now remove the route
        dummy.removeRoute('DUMMY', (':id', 'dummy'), dummy.handler)
        self.assertRaises(RestException, dummy.handleRoute, 'DUMMY',
                          ('guid', 'dummy'), {})

    def testCORS(self):
        testServer.root.api.v1.dummy = DummyResource()

        # When no origin header is passed, we shouldn't receive CORS headers
        resp = self.request(path='/dummy/test')
        self.assertStatusOk(resp)
        self.assertFalse('Access-Control-Allow-Origin' in resp.headers)
        self.assertFalse('Access-Control-Allow-Credentials' in resp.headers)

        # If no origins are allowed, we should not get an allow origin header
        resp = self.request(path='/dummy/test', additionalHeaders=[
            ('Origin', 'http://foo.com')
        ])
        self.assertStatusOk(resp)
        self.assertFalse('Access-Control-Allow-Origin' in resp.headers)

        # If we allow some origins, we should get the corresponding header
        self.model('setting').set(SettingKey.CORS_ALLOW_ORIGIN,
                                  'http://kitware.com')
        resp = self.request(path='/dummy/test', additionalHeaders=[
            ('Origin', 'http://foo.com')
        ])
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                         'http://kitware.com')
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                         'true')

        # Simulate a preflight request; we should get back several headers
        self.model('setting').set(SettingKey.CORS_ALLOW_METHODS, 'POST')
        resp = self.request(
            path='/dummy/test', method='OPTIONS', additionalHeaders=[
                ('Origin', 'http://foo.com')
            ], isJson=False
        )
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), '')
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                         'http://kitware.com')
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'],
                         'true')
        self.assertEqual(resp.headers['Access-Control-Allow-Headers'],
                         SettingDefault.defaults[SettingKey.CORS_ALLOW_HEADERS])
        self.assertEqual(resp.headers['Access-Control-Allow-Methods'], 'POST')

        # Set multiple allowed origins
        self.model('setting').set(SettingKey.CORS_ALLOW_ORIGIN,
                                  'http://foo.com, http://bar.com')
        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://bar.com')
            ], isJson=False)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'],
                         'http://bar.com')

        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://invalid.com')
            ], isJson=False)
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
