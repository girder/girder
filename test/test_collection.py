import pytest
import json

from girder.models.collection import Collection
from pytest_girder.assertions import assertStatusOk

METADATA = {
    'key': 'value',
    'apple': 'fruit'
}


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
def oldCollection(db, collection):
    del collection['meta']
    collection = Collection().save(collection)
    assert 'meta' not in collection
    yield collection


@pytest.fixture
def oldCollections(db, collections):
    for i, collection in enumerate(collections):
        del collection['meta']
        collections[i] = Collection().save(collection)
        assert 'meta' not in collections[i]
    yield collections


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


def testSingleOldCollectionMetaExists(server, oldCollection, admin):
    resp = server.request(path='/collection/%s' % oldCollection['_id'], user=admin)
    assertStatusOk(resp)
    assert 'meta' in resp.json


def testListCollectionMetaExists(server, collections, admin):
    resp = server.request(path='/collection', user=admin)
    assertStatusOk(resp)
    assert all(('meta' in x) for x in resp.json)


def testListOldCollectionMetaExists(server, oldCollections, admin):
    resp = server.request(path='/collection', user=admin)
    assertStatusOk(resp)
    assert all(('meta' in x) for x in resp.json)


def testCollectionSetMetadata(server, collection, admin):
    resp = server.request(
        path='/collection/%s/metadata' % collection['_id'],
        user=admin,
        method='PUT',
        body=json.dumps(METADATA),
        type='application/json')

    assertStatusOk(resp)
    assert resp.json['meta'] == METADATA

    # Check that fetching the object again yields the same result
    newDoc = server.request(
        path='/collection/%s' % collection['_id'],
        user=admin,
        method='GET')

    assert newDoc.json['meta'] == METADATA


def testCollectionDeleteMetadata(server, collection, admin):
    collection = Collection().setMetadata(collection, METADATA)
    resp = server.request(
        path='/collection/%s/metadata' % collection['_id'],
        user=admin,
        method='DELETE',
        body=json.dumps(list(METADATA.keys())),
        type='application/json')
    assertStatusOk(resp)
    assert resp.json['meta'] != METADATA
    assert resp.json['meta'] == {}

    newDoc = server.request(
        path='/collection/%s' % collection['_id'],
        user=admin,
        method='GET')
    assert newDoc.json['meta'] != METADATA
    assert newDoc.json['meta'] == {}


# Model Layer
def testCollectionModelSetMetadata(collection):
    updatedCollection = Collection().setMetadata(collection, METADATA)
    assert updatedCollection['meta'] == METADATA


# Model Layer
def testCollectionModelDeleteMetadata(collection):
    collection = Collection().setMetadata(collection, METADATA)
    noMeta = Collection().deleteMetadata(collection, list(METADATA.keys()))
    assert noMeta['meta'] == {}


# Model Layer
def testCollectionLoad(collection, admin):
    loadedCollection = Collection().load(collection['_id'], user=admin)
    assert 'meta' in loadedCollection


# Model Layer
def testCollectionFilter(collection):
    loadedCollection = Collection().filter(collection)
    assert 'meta' in loadedCollection
