import pytest

from .. import test_access
from girder.api import access
from pytest_girder.assertions import assertStatus, assertStatusOk

test_access_server = test_access.server
public_endpoints = test_access.public_endpoints + [
    '/accesstest/test_always_public',
]
user_endpoints = test_access.user_endpoints


@access.public
def alwaysPublicHandler(**kwargs):
    return


alwaysPublicHandler.alwaysPublic = True


@pytest.fixture
def server(test_access_server):
    server = test_access_server
    accesstest = server.root.api.v1.accesstest
    accesstest.route('GET', ('test_always_public', ), alwaysPublicHandler)
    yield server


@pytest.mark.plugin('disable_public_access')
@pytest.mark.parametrize('endpoint', public_endpoints)
def testPublicCanAccessPublicEndpoints(server, endpoint):
    resp = server.request(path=endpoint, method='GET')
    if 'scoped_public' in endpoint or 'always_public' in endpoint:
        assertStatusOk(resp)
    else:
        assertStatus(resp, 401)


@pytest.mark.plugin('disable_public_access')
@pytest.mark.parametrize('endpoint', public_endpoints + user_endpoints)
def testUserCanAccessPublicEndpointsOnNonPublicServer(server, user, endpoint):
    resp = server.request(path=endpoint, method='GET', user=user)
    assertStatusOk(resp)
