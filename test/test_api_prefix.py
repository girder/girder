import pytest
from pytest_girder.assertions import assertStatusOk

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, Prefix
from girder.plugin import GirderPlugin


class Resourceful(Resource):
    def __init__(self):
        super(Resourceful, self).__init__()

        self.route('GET', (), self.getResource, resource=self)

    @access.public
    @describeRoute(
        Description('Get something.')
    )
    def getResource(self, params):
        return ['custom REST route']


class APIPrefix(GirderPlugin):
    def load(self, info):
        info['apiRoot'].prefix = Prefix()
        info['apiRoot'].prefix.resourceful = Resourceful()
        info['apiRoot'].prefix.sibling = Resourceful()


@pytest.mark.plugin('has_api_prefix', APIPrefix)
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
