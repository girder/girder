import pytest
from pytest_girder.assertions import assertStatusOk


@pytest.mark.testPlugin('has_api_prefix')
@pytest.mark.parametrize('route', [
    '/prefix/resourceful',
    '/prefix/sibling'
])
def testCustomWebRoot(route, server):
    """
    Tests the ability of plugins to serve their own custom server roots.
    """
    resp = server.request(route)
    assertStatusOk(resp)
    assert resp.json == ['custom REST route']
