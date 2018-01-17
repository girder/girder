import pytest

from pytest_girder.assertions import assertStatus, assertStatusOk
from pytest_girder.utils import getResponseBody
from six.moves.urllib.parse import urlparse


@pytest.mark.testPlugin('test_plugin')
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


@pytest.mark.testPlugin('test_plugin')
def testPluginRestRoutes(server):
    resp = server.request('/describe')
    assertStatusOk(resp)
    assert '/other' in resp.json['paths']

    resp = server.request('/other')
    assertStatusOk(resp)
    assert resp.json == ['custom REST route']
