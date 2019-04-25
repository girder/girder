import pytest

from girder.models.collection import Collection
from pytest_girder.assertions import assertStatusOk


@pytest.fixture
def collections(db):
    yield (
        Collection().createCollection('private collection', public=False),
        Collection().createCollection('public collection', public=True)
    )


@pytest.fixture
def users(admin, user):
    yield (admin, user, None)


@pytest.mark.parametrize('userIdx,expected', [
    (0, 2),
    (1, 1),
    (2, 1)
])
def testCollectionsCount(server, userIdx, expected, collections, users):
    resp = server.request(path='/collection/details', user=users[userIdx])
    assertStatusOk(resp)
    assert resp.json['nCollections'] == expected
