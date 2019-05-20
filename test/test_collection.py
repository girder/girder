import pytest
import json

from girder.models.collection import Collection
from pytest_girder.assertions import assertStatusOk


@pytest.fixture
def collections(db):
    yield [
        Collection().createCollection('private collection', public=False),
        Collection().createCollection('public collection', public=True)
    ]


@pytest.fixture
def collection(db):
    yield Collection().createCollection('public collection', public=True)


@pytest.fixture
def collectionWithMeta(db, collection, metadata):
    def _collectionWithMeta(_metadata=None):
        if _metadata is None:
            _metadata = metadata
        return Collection().setMetadata(collection, _metadata)

    yield _collectionWithMeta


@pytest.fixture
def metadata():
    return {
        'key': 'value',
        'apple': 'fruit'
    }


@pytest.fixture
def users(admin, user):
    yield [admin, user, None]


@pytest.mark.parametrize('userIdx,expected', [
    (0, 2),
    (1, 1),
    (2, 1)
])
def testCollectionsCount(server, userIdx, expected, collections, users):
    resp = server.request(path='/collection/details', user=users[userIdx])
    assertStatusOk(resp)
    assert resp.json['nCollections'] == expected


def testSingleCollectionMetaExists(server, collection, admin):
    resp = server.request(path='/collection/%s' % collection['_id'], user=admin)
    assertStatusOk(resp)
    assert 'meta' in resp.json


def testListCollectionMetaExists(server, collection, admin):
    resp = server.request(path='/collection', user=admin)
    assertStatusOk(resp)
    assert all(('meta' in x) for x in resp.json)


def testCollectionSetMetadata(server, collection, metadata, admin):
    resp = server.request(
        path='/collection/%s/metadata' % collection['_id'],
        user=admin,
        method='PUT',
        body=json.dumps(metadata),
        type='application/json')

    assertStatusOk(resp)
    assert resp.json['meta'] == metadata

    # Check that fetching the object again yields the same result
    newDoc = server.request(
        path='/collection/%s' % collection['_id'],
        user=admin,
        method='GET')

    assert newDoc.json['meta'] == metadata


def testCollectionDeleteMetadata(server, collectionWithMeta, metadata, admin):
    collection = collectionWithMeta(metadata)
    resp = server.request(
        path='/collection/%s/metadata' % collection['_id'],
        user=admin,
        method='DELETE',
        body=json.dumps(list(metadata.keys())),
        type='application/json')
    assertStatusOk(resp)
    assert resp.json['meta'] != metadata
    assert resp.json['meta'] == {}

    newDoc = server.request(
        path='/collection/%s' % collection['_id'],
        user=admin,
        method='GET')
    assert newDoc.json['meta'] != metadata
    assert newDoc.json['meta'] == {}


# Model Layer
def testCollectionModelSetMetadata(collection, metadata):
    updatedCollection = Collection().setMetadata(collection, metadata)
    assert updatedCollection['meta'] == metadata


# Model Layer
def testCollectionModelDeleteMetadata(collectionWithMeta, metadata):
    collection = collectionWithMeta(metadata)
    noMeta = Collection().deleteMetadata(collection, list(metadata.keys()))
    assert noMeta['meta'] == {}


# Model Layer
def testCollectionLoad(collection, admin):
    loadedCollection = Collection().load(collection['_id'], user=admin)
    assert 'meta' in loadedCollection


# Model Layer
def testCollectionFilter(collection):
    loadedCollection = Collection().filter(collection)
    assert 'meta' in loadedCollection
