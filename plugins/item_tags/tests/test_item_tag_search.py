import pytest
from pytest_girder.assertions import assertStatusOk

from girder.models.folder import Folder
from girder.models.item import Item


@pytest.fixture
def userFolder(user, fsAssetstore):
    folders = Folder().childFolders(
        parent=user, parentType='user', user=user
    )
    for folder in folders:
        if folder['public'] is True:
            return folder


@pytest.fixture
def adminFolder(admin, fsAssetstore):
    folders = Folder().childFolders(
        parent=admin, parentType='user', user=admin
    )
    for folder in folders:
        if folder['public'] is True:
            return folder


def createItem(name, user, folder, tags):
    item = Item().createItem(name, user, folder)
    return Item().setMetadata(item, {'girder_item_tags': tags})


@pytest.mark.plugin('item_tags')
def test_search_case_insensitive(server, user, userFolder):
    item = createItem('testItem', user, userFolder, ['AbC'])
    resp = server.request(
        path='/resource/search',
        method='GET',
        user=user,
        params={
            'q': 'aBc',
            'mode': 'item_tags',
            'types': '["item"]'
        }
    )
    assertStatusOk(resp)
    results = resp.json['item']
    print(results)
    assert len(results) == 1
    assert results[0]['_id'] == str(item['_id'])


@pytest.mark.plugin('item_tags')
def test_search_multiple_results(server, user, userFolder):
    item1 = createItem('testItem1', user, userFolder, ['abc', '123'])
    item2 = createItem('testItem2', user, userFolder, ['xyz', 'abc'])
    createItem('testItem3', user, userFolder, ['123', 'xyz'])
    resp = server.request(
        path='/resource/search',
        method='GET',
        user=user,
        params={
            'q': 'abc',
            'mode': 'item_tags',
            'types': '["item"]'
        }
    )
    assertStatusOk(resp)
    results = resp.json['item']
    print(results)
    assert len(results) == 2
    assert results[0]['_id'] == str(item1['_id'])
    assert results[1]['_id'] == str(item2['_id'])


@pytest.mark.plugin('item_tags')
def test_search_multiple_search_tags(server, user, userFolder):
    createItem('testItem1', user, userFolder, ['abc', '123'])
    item2 = createItem('testItem2', user, userFolder, ['xyz', 'abc'])
    createItem('testItem3', user, userFolder, ['123', 'xyz'])
    resp = server.request(
        path='/resource/search',
        method='GET',
        user=user,
        params={
            'q': 'abc xyz',
            'mode': 'item_tags',
            'types': '["item"]'
        }
    )
    assertStatusOk(resp)
    results = resp.json['item']
    print(results)
    assert len(results) == 1
    assert results[0]['_id'] == str(item2['_id'])
