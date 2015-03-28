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
from girder.api.describe import Description
from girder.api.rest import Resource, RestException
from girder.constants import SettingKey

testServer = None


def setUpModule():
    global testServer
    testServer = base.startServer()


def tearDownModule():
    base.stopServer()


class DummyResource(Resource):
    def __init__(self):
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
    def handler(self, **kwargs):
        return kwargs
    # We want to test adding and removing documentation when we add and remove
    # routes.
    handler.description = (
        Description('Dummy handler.'))


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

    def _testOrigin(self, origin=None, results={}, headers={}, useHttps=False):
        """
        Test CORS responses by querying the dummy endpoints for each method.

        :param origin: the origin to use in the request, or None for no
                       origin header.
        :param results: a dictionary.  The keys are methods and the values are
                        the expected HTTP response code.  Any method that isn't
                        expected to return a 200 must be present.
        :param headers: a dictionary of additional headers to send.
        :param useHttps: if True, pretend to use https.
        """
        methods = ['GET', 'PUT', 'POST', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']
        additionalHeaders = []
        if headers:
            for key in headers:
                additionalHeaders.append((key, headers[key]))
        if origin:
            additionalHeaders.append(('Origin', origin))
        for method in methods:
            resp = self.request(
                path='/dummy/test', method=method, isJson=False,
                params={'key': 'value'}, additionalHeaders=additionalHeaders,
                useHttps=useHttps)
            self.assertStatus(resp, results.get(method, 200))

    def testCORS(self):
        testServer.root.api.v1.dummy = DummyResource()

        # Without an origin, the query comes from ourselves, so it should all
        # be fine, except OPTIONS, which doesn't acknowlege its presence
        self._testOrigin(None, {'OPTIONS': 405})
        # If we specify an origin of ourselves, there should be no change
        self._testOrigin('http://127.0.0.1', {'OPTIONS': 405})
        # If we specify a different origin, simple queries are allowed and
        # everything else should be refused
        self._testOrigin('http://kitware.com', {
            'PUT': 403, 'DELETE': 403, 'PATCH': 403, 'OPTIONS': 405})
        # If we have a X-Forward-Host that contains ourselves, even thouugh
        # the origin is different, then it should be just like coming from
        # ourselves
        self._testOrigin('http://kitware.com', {'OPTIONS': 405},
                         headers={'X-Forwarded-Host': 'kitware.com'})
        # But a different X-Forwarded-Host should be like a different origin
        self._testOrigin('http://kitware.com', {
            'PUT': 403, 'DELETE': 403, 'PATCH': 403, 'OPTIONS': 405},
            headers={'X-Forwarded-Host': 'www.kitware.com'})

        # Set a single allowed origin
        self.model('setting').set(SettingKey.CORS_ALLOW_ORIGIN,
                                  'http://kitware.com')
        # Without an origin, nothing should be different
        self._testOrigin(None, {'OPTIONS': 405})
        # If we specify an origin of ourselves, everything should work
        self._testOrigin('http://127.0.0.1')
        # As should the allowed origin
        self._testOrigin('http://kitware.com')
        # If we specify a different origin, non-simple queries should be
        # refused
        self._testOrigin('http://girder.kitware.com', {
            'PUT': 403, 'DELETE': 403, 'PATCH': 403, 'OPTIONS': 405})

        # Set a list of allowed origins
        self.model('setting').set(
            SettingKey.CORS_ALLOW_ORIGIN,
            'http://kitware.com,http://girder.kitware.com,'
            'https://secure.kitware.com')
        self._testOrigin(None, {'OPTIONS': 405})
        self._testOrigin('http://127.0.0.1')
        self._testOrigin('http://kitware.com')
        self._testOrigin('http://girder.kitware.com')

        # Test origins with paths and https.  None should cause a problem
        self._testOrigin('http://kitware.com/girder')
        self._testOrigin('https://secure.kitware.com',
                         headers={'X-Forwarded-Host': 'secure.kitware.com'},
                         useHttps=True)
        self._testOrigin('http://secure.kitware.com',
                         headers={'X-Forwarded-Host': 'secure.kitware.com'},
                         useHttps=False)
        self._testOrigin('http://kitware.com',
                         headers={'X-Forwarded-Host': 'kitware.com/girder'})

        # If we specify a different origin, everything should be refused
        self._testOrigin('http://girder2.kitware.com', {
            'PUT': 403, 'DELETE': 403, 'PATCH': 403, 'OPTIONS': 405})

        # Specifying the wildcard should allow everything
        self.model('setting').set(SettingKey.CORS_ALLOW_ORIGIN, '*')
        self._testOrigin(None, {'OPTIONS': 405})
        self._testOrigin('http://127.0.0.1')
        self._testOrigin('http://kitware.com')
        self._testOrigin('http://girder.kitware.com')
        self._testOrigin('http://girder2.kitware.com')

        # If we set the methods, then only those methods are allowed for
        # non-local origins
        self.model('setting').set(SettingKey.CORS_ALLOW_METHODS,
                                  'GET,PUT,POST,HEAD')
        # For ourselves, everything is allowed
        self._testOrigin(None, {'OPTIONS': 405})
        self._testOrigin('http://127.0.0.1')
        self._testOrigin('http://kitware.com', {'DELETE': 403, 'PATCH': 403})
        self.model('setting').set(SettingKey.CORS_ALLOW_METHODS, '')

        # Custom headers should fail until we approve them.  Case shouldn't
        # matter
        headers = {'x-cUstom': 'test'}
        self._testOrigin('http://kitware.com',
                         {'PUT': 403, 'DELETE': 403, 'PATCH': 403}, headers)
        # Before we specify anything, a few headers should go through
        headersDefault = {'Authorization': 'password'}
        self._testOrigin('http://kitware.com', headers=headersDefault)
        # Allow our custom header
        self.model('setting').set(SettingKey.CORS_ALLOW_HEADERS, 'X-Custom')
        self._testOrigin('http://kitware.com', headers=headers)
        # And now our default is no longer there
        self._testOrigin('http://kitware.com',
                         {'PUT': 403, 'DELETE': 403, 'PATCH': 403},
                         headersDefault)
        # Our header can be one in a list
        self.model('setting').set(SettingKey.CORS_ALLOW_HEADERS,
                                  'X-Test,X-Custom,Authorization')
        self._testOrigin('http://kitware.com', headers=headers)
        self._testOrigin('http://kitware.com', headers=headersDefault)
