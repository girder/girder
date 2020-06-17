# -*- coding: utf-8 -*-
import os
import requests

from .. import base
from girder import config
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource
from girder.exceptions import GirderException, RestException
from girder.models.setting import Setting
from girder.settings import SettingDefault, SettingKey

testServer = None


def setUpModule():
    global testServer
    os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
    config.loadConfig()
    testServer = base.startServer(mock=False)


def tearDownModule():
    base.stopServer()


class DummyResource(Resource):
    def __init__(self):
        super().__init__()
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
        # Test an empty route handler
        emptyResource = Resource()
        self.assertRaises(GirderException, emptyResource.handleRoute, 'GET', (), {})

        dummy = DummyResource()

        # Bad route should give a useful exception.
        exc = None
        try:
            dummy.handleRoute('GET', (), {})
        except RestException as e:
            exc = str(e)
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

        # Test getting the route handler
        self.assertRaises(Exception, dummy.getRouteHandler, 'FOO', (':id', 'dummy'))
        self.assertRaises(Exception, dummy.getRouteHandler, 'DUMMY', (':id', 'foo'))
        registeredHandler = dummy.getRouteHandler('DUMMY', (':id', 'dummy'))
        # The handler method cannot be compared directly with `is`, but its name and behavior can be
        # examined
        self.assertEqual(registeredHandler.__name__, dummy.handler.__name__)
        self.assertEqual(registeredHandler(foo=42), {'foo': 42})

        # Now remove the route
        dummy.removeRoute('DUMMY', (':id', 'dummy'))
        self.assertRaises(RestException, dummy.handleRoute, 'DUMMY', ('guid', 'dummy'), {})

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

        # Request from a non-allowed Origin
        Setting().set(SettingKey.CORS_ALLOW_ORIGIN, 'http://kitware.com')
        resp = self.request(path='/dummy/test', additionalHeaders=[
            ('Origin', 'http://foo.com')
        ])
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'], 'true')

        # Simulate a preflight request; we should get back several headers
        Setting().set(SettingKey.CORS_ALLOW_METHODS, 'POST')
        resp = self.request(
            path='/dummy/test', method='OPTIONS', additionalHeaders=[
                ('Origin', 'http://foo.com')
            ], isJson=False
        )
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), '')

        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Credentials'], 'true')
        self.assertEqual(resp.headers['Access-Control-Allow-Headers'],
                         SettingDefault.defaults[SettingKey.CORS_ALLOW_HEADERS])
        self.assertEqual(resp.headers['Access-Control-Allow-Methods'], 'POST')

        # Make an actual preflight request with query parameters; CherryPy 11.1
        # introduced a bug where this would fail with a 405.
        resp = requests.options(
            'http://127.0.0.1:%s/api/v1/folder?key=value' % os.environ['GIRDER_TEST_PORT'])
        self.assertEqual(resp.status_code, 200)

        # Set multiple allowed origins
        Setting().set(SettingKey.CORS_ALLOW_ORIGIN, 'http://foo.com, http://bar.com')
        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://bar.com')
            ], isJson=False)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], 'http://bar.com')

        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://invalid.com')
            ], isJson=False)
        self.assertNotIn('Access-Control-Allow-Origin', resp.headers)

        # Test behavior of '*' allowed origin
        Setting().set(SettingKey.CORS_ALLOW_ORIGIN, 'http://foo.com,*')
        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://bar.com')
            ], isJson=False)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

        resp = self.request(
            path='/dummy/test', method='GET', additionalHeaders=[
                ('Origin', 'http://foo.com')
            ], isJson=False)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], 'http://foo.com')
