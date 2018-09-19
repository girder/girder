
import os
import pytest

from pytest_girder.assertions import assertStatus, assertStatusOk
from pytest_girder.utils import getResponseBody
from six.moves.urllib.parse import urlparse

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import boundHandler, rawResponse, Resource, setResponseHeader
from girder.api.v1.collection import Collection
from girder.constants import TokenScope
from girder.utility.server import staticFile
from girder.plugin import GirderPlugin


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler
@describeRoute(None)
def unboundHandlerDefaultNoArgs(self, params):
    self.requireParams('val', params)
    return not self.boolParam('val', params)


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler()
@describeRoute(None)
def unboundHandlerDefault(self, params):
    self.requireParams('val', params)
    return not self.boolParam('val', params)


@access.user(scope=TokenScope.ANONYMOUS_SESSION)
@boundHandler(Collection())
@describeRoute(None)
def unboundHandlerExplicit(self, params):
    currentUser = self.getCurrentUser()
    return {
        'userLogin': currentUser['login'] if currentUser else None,
        'name': self.resourceName
    }


class CustomAppRoot(object):
    """
    The webroot endpoint simply serves the main index HTML file.
    """
    exposed = True

    def GET(self):
        return "hello world from test_plugin"


class Other(Resource):
    def __init__(self):
        super(Other, self).__init__()
        self.resourceName = 'other'

        self.route('GET', (), self.getResource)
        self.route('GET', ('rawWithDecorator',), self.rawWithDecorator)
        self.route('GET', ('rawReturningText',), self.rawReturningText)
        self.route('GET', ('rawInternal',), self.rawInternal)

    @access.public
    @rawResponse
    @describeRoute(None)
    def rawWithDecorator(self, params):
        return b'this is a raw response'

    @access.public
    @rawResponse
    @describeRoute(None)
    def rawReturningText(self, params):
        setResponseHeader('Content-Type', 'text/plain')
        return u'this is not encoded \U0001F44D'

    @access.public
    @describeRoute(None)
    def rawInternal(self, params):
        self.setRawResponse()
        return b'this is also a raw response'

    @access.public
    @describeRoute(
        Description('Get something.')
    )
    def getResource(self, params):
        return ['custom REST route']


class CustomRoot(GirderPlugin):
    def load(self, info):
        info['serverRoot'], info['serverRoot'].girder = (
            CustomAppRoot(), info['serverRoot'])
        info['serverRoot'].api = info['serverRoot'].girder.api
        del info['serverRoot'].girder.api

        info['apiRoot'].collection.route('GET', ('unbound', 'default', 'noargs'),
                                         unboundHandlerDefaultNoArgs)
        info['apiRoot'].collection.route('GET', ('unbound', 'default'),
                                         unboundHandlerDefault)
        info['apiRoot'].collection.route('GET', ('unbound', 'explicit'),
                                         unboundHandlerExplicit)

        info['apiRoot'].other = Other()
        path = os.path.join(os.path.dirname(__file__), 'data', 'static.txt')
        info['serverRoot'].static_route = staticFile(path)


@pytest.mark.plugin('test_plugin', CustomRoot)
@pytest.mark.parametrize('route,text', [
    ('/', 'hello world from test_plugin'),
    ('/girder', 'g-global-info-apiroot'),
    ('/api/v1', 'Girder REST API Documentation'),
    ('/static_route', 'Hello world!')
])
def testPluginRoutesForHumans(server, route, text):
    resp = server.request(route, prefix='', isJson=False)
    assertStatusOk(resp)
    assert text in getResponseBody(resp)


def testServerInfoInErrorPage(server):
    # For security, we want to ensure cherrypy does not appear in server info
    resp = server.request('/girder/api/v1', prefix='', isJson=False)
    assertStatus(resp, 404)
    body = getResponseBody(resp).lower()
    server = resp.headers['Server'].lower()
    assert 'cherrypy' not in body + server
    assert 'girder' in body
    assert 'girder' in server


def testApiRedirect(server):
    resp = server.request('/api', prefix='', isJson=False)
    assertStatus(resp, 303)
    assert urlparse(resp.headers['Location']).path == '/api/v1'


@pytest.mark.plugin('test_plugin', CustomRoot)
def testPluginRestRoutes(server):
    resp = server.request('/describe')
    assertStatusOk(resp)
    assert '/other' in resp.json['paths']

    resp = server.request('/other')
    assertStatusOk(resp)
    assert resp.json == ['custom REST route']
