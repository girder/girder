import pytest
from bson.objectid import ObjectId

from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility import assetstore_usage
from pytest_girder.assertions import assertStatus, assertStatusOk


def _makeFile(creator, store, name, size, path, item=None, attachedTo=None, imported=False):
    file = File().createFile(
        creator=creator, item=item, name=name, size=size, assetstore=store, saveFile=False)
    file['path'] = path
    file['sha512'] = path * 4
    if imported:
        file['imported'] = True
    if attachedTo is not None:
        file['attachedToType'], file['attachedToId'] = attachedTo
    return File().save(file)


@pytest.fixture(params=['databaseJoin', 'itemLookup'])
def usageData(request, db, admin, fsAssetstore, tmp_path, monkeypatch):
    # Exercise both ways of joining items to folders.
    monkeypatch.setattr(
        assetstore_usage, 'LARGE_ASSETSTORE_FILES', 0 if request.param == 'databaseJoin' else 1e9)
    assetstore_usage.clearCache()
    store1 = fsAssetstore
    store2 = Assetstore().createFilesystemAssetstore('second', str(tmp_path / 'second'))
    data = Folder().createFolder(admin, 'data', parentType='user', creator=admin)
    sub = Folder().createFolder(data, 'sub', creator=admin)
    coll = Collection().createCollection('coll', creator=admin)
    collFolder = Folder().createFolder(coll, 'cf', parentType='collection', creator=admin)
    item1 = Item().createItem('item1', creator=admin, folder=data)
    item2 = Item().createItem('item2', creator=admin, folder=sub)
    item3 = Item().createItem('item3', creator=admin, folder=collFolder)
    item4 = Item().createItem('item4', creator=admin, folder=collFolder)
    files = {
        'f1': _makeFile(admin, store1, 'f1', 100, 'aa', item=item1),
        'f2': _makeFile(admin, store2, 'f2', 200, 'bb', item=item1),
        'f3': _makeFile(admin, store1, 'f3', 1000, 'cc', item=item2),
        'f4': _makeFile(admin, store1, 'f4', 50, '/abs/dd', item=item3, imported=True),
        'subAttached': _makeFile(
            admin, store1, 'thumb', 7, 'ee', attachedTo=('folder', sub['_id'])),
        'userAttached': _makeFile(
            admin, store1, 'avatar', 3, 'gg', attachedTo=('user', admin['_id'])),
        'otherAttached': _makeFile(
            admin, store1, 'annotation', 11, 'hh',
            attachedTo=(['annotation', 'large_image'], ObjectId())),
        'orphan': _makeFile(admin, store1, 'orphan', 13, 'ii', item=item1),
    }
    # Point the orphan at an item that doesn't exist.
    File().collection.update_one(
        {'_id': files['orphan']['_id']}, {'$set': {'itemId': ObjectId()}})
    files['copy'] = File().copyFile(files['f3'], admin, item=item4)
    yield {
        'store1': store1, 'store2': store2, 'data': data, 'sub': sub, 'coll': coll,
        'collFolder': collFolder, 'item1': item1, 'item2': item2, 'item3': item3,
        'item4': item4, 'files': files,
    }
    assetstore_usage.clearCache()


def _usage(server, admin, **params):
    resp = server.request('/assetstore/usage', user=admin, params=params)
    assertStatusOk(resp)
    return resp.json


def _sizes(result):
    return {(child['type'], child['name']): (child['size'], child['count'])
            for child in result['children']}


def testUsageTopLevel(server, admin, usageData):
    result = _usage(server, admin, assetstoreId=usageData['store1']['_id'])
    assert _sizes(result) == {
        ('user', admin['login']): (1110, 4),
        ('collection', 'coll'): (1050, 2),
        ('orphaned', 'Orphaned files'): (13, 1),
        ('otherAttached', 'Files attached to other resources'): (11, 1),
    }
    assert [child['type'] for child in result['children']] == [
        'user', 'collection', 'orphaned', 'otherAttached']
    assert result['node']['size'] == 2184
    assert result['node']['count'] == 8
    assert result['breadcrumbs'] == []
    assert result['other'] == {'size': 0, 'count': 0, 'nodes': 0}
    assert [f['name'] for f in result['topFiles'][:3]] == ['f3', 'f3', 'f1']
    top = result['topFiles'][0]
    assert top['resourceType'] == 'item'
    assert top['resourceName'] in ('item2', 'item4')
    assert top['resourcePath'] in (
        '/user/%s/data/sub/item2' % admin['login'], '/collection/coll/cf/item4')
    paths = {f['name']: f['resourcePath'] for f in result['topFiles']}
    assert paths['avatar'] == '/user/%s' % admin['login']
    assert paths['orphan'] is None

    result = _usage(server, admin)
    assert _sizes(result)[('user', admin['login'])] == (1310, 5)
    assert result['assetstoreId'] is None


def testUsageFlags(server, admin, usageData):
    store1 = usageData['store1']['_id']
    result = _usage(server, admin, assetstoreId=store1, dedup=True)
    assert _sizes(result)[('collection', 'coll')] == (50, 1)
    assert _sizes(result)[('user', admin['login'])] == (1110, 4)
    assert [f['name'] for f in result['topFiles'][:2]] == ['f3', 'f1']
    assert result['topFiles'][0]['_id'] == str(usageData['files']['f3']['_id'])

    result = _usage(server, admin, assetstoreId=store1, source='imported')
    assert _sizes(result) == {('collection', 'coll'): (50, 1)}
    assert [f['name'] for f in result['topFiles']] == ['f4']
    assert result['topFiles'][0]['imported'] is True

    result = _usage(server, admin, assetstoreId=store1, source='uploaded')
    assert _sizes(result)[('collection', 'coll')] == (1000, 1)
    assert _sizes(result)[('user', admin['login'])] == (1110, 4)

    result = _usage(server, admin, assetstoreId=store1, attached=False)
    assert _sizes(result) == {
        ('user', admin['login']): (1100, 2),
        ('collection', 'coll'): (1050, 2),
        ('orphaned', 'Orphaned files'): (13, 1),
    }
    assert 'thumb' not in [f['name'] for f in result['topFiles']]


def testUsageDrillDown(server, admin, usageData):
    store1 = usageData['store1']['_id']
    result = _usage(server, admin, assetstoreId=store1, parentType='user', parentId=admin['_id'])
    assert _sizes(result) == {
        ('folder', 'data'): (1107, 3),
        ('attached', 'Attached files'): (3, 1),
    }
    assert result['node']['size'] == 1110
    assert [b['name'] for b in result['breadcrumbs']] == [admin['login']]
    assert [f['name'] for f in result['topFiles']] == ['f3', 'f1', 'thumb', 'avatar']

    result = _usage(server, admin, assetstoreId=store1, parentType='folder',
                    parentId=usageData['data']['_id'])
    assert _sizes(result) == {('folder', 'sub'): (1007, 2), ('item', 'item1'): (100, 1)}
    assert result['node']['size'] == 1107

    result = _usage(server, admin, assetstoreId=store1, parentType='folder',
                    parentId=usageData['sub']['_id'])
    assert _sizes(result) == {('item', 'item2'): (1000, 1), ('attached', 'Attached files'): (7, 1)}
    assert [b['name'] for b in result['breadcrumbs']] == [admin['login'], 'data', 'sub']
    assert [f['name'] for f in result['topFiles']] == ['f3', 'thumb']
    assert result['topFiles'][1]['resourceType'] == 'folder'
    assert result['topFiles'][1]['resourcePath'] == '/user/%s/data/sub' % admin['login']

    result = _usage(server, admin, parentType='item', parentId=usageData['item1']['_id'])
    assert _sizes(result) == {('file', 'f2'): (200, 1), ('file', 'f1'): (100, 1)}
    assert all(not child['drillable'] for child in result['children'])
    assert [b['type'] for b in result['breadcrumbs']] == ['user', 'folder', 'item']

    result = _usage(server, admin, assetstoreId=store1, dedup=True, parentType='collection',
                    parentId=usageData['coll']['_id'])
    assert _sizes(result) == {('folder', 'cf'): (50, 1)}
    result = _usage(server, admin, assetstoreId=store1, dedup=True, parentType='folder',
                    parentId=usageData['collFolder']['_id'])
    assert _sizes(result) == {('item', 'item3'): (50, 1)}


def testUsageLimitAndCache(server, admin, usageData):
    store1 = usageData['store1']['_id']
    result = _usage(server, admin, assetstoreId=store1, limit=1, topFiles=2)
    assert len(result['children']) == 1
    assert result['other'] == {'size': 1074, 'count': 4, 'nodes': 3}
    assert len(result['topFiles']) == 2

    cached = _usage(server, admin, assetstoreId=store1)
    assert cached['computed'] == result['computed']
    _makeFile(admin, usageData['store1'], 'late', 5, 'jj', item=usageData['item1'])
    assert _usage(server, admin, assetstoreId=store1)['node']['size'] == 2184
    refreshed = _usage(server, admin, assetstoreId=store1, refresh=True)
    assert refreshed['node']['size'] == 2189


def testUsageAccessAndValidation(server, admin, user, usageData):
    resp = server.request('/assetstore/usage', user=user)
    assertStatus(resp, 403)
    resp = server.request('/assetstore/usage', user=admin, params={'parentType': 'folder'})
    assertStatus(resp, 400)
    resp = server.request('/assetstore/usage', user=admin, params={
        'parentType': 'folder', 'parentId': str(ObjectId())})
    assertStatus(resp, 400)
    resp = server.request('/assetstore/usage', user=admin, params={'source': 'bogus'})
    assertStatus(resp, 400)


def testUsageDedupOfAttachedFiles(server, admin, usageData):
    store1 = usageData['store1']
    thumb = _makeFile(
        admin, store1, 'itemthumb', 17, 'kk', attachedTo=('item', usageData['item1']['_id']))
    copy = File().copyFile(thumb, admin)
    File().collection.update_one(
        {'_id': copy['_id']}, {'$set': {'attachedToId': usageData['item3']['_id']}})

    result = _usage(server, admin, assetstoreId=store1['_id'])
    assert _sizes(result)[('user', admin['login'])] == (1127, 5)
    assert _sizes(result)[('collection', 'coll')] == (1067, 3)
    result = _usage(server, admin, assetstoreId=store1['_id'], dedup=True)
    assert _sizes(result)[('user', admin['login'])] == (1127, 5)
    assert _sizes(result)[('collection', 'coll')] == (50, 1)

    result = _usage(server, admin, assetstoreId=store1['_id'], parentType='folder',
                    parentId=usageData['data']['_id'])
    assert _sizes(result)[('item', 'item1')] == (117, 2)
    result = _usage(server, admin, assetstoreId=store1['_id'], parentType='item',
                    parentId=usageData['item3']['_id'])
    assert _sizes(result) == {('file', 'f4'): (50, 1), ('file', 'itemthumb'): (17, 1)}
    assert [f['name'] for f in result['topFiles']] == ['f4', 'itemthumb']
    result = _usage(server, admin, assetstoreId=store1['_id'], dedup=True, parentType='item',
                    parentId=usageData['item3']['_id'])
    assert _sizes(result) == {('file', 'f4'): (50, 1)}
    assert [f['name'] for f in result['topFiles']] == ['f4']
