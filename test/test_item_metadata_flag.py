import json

import pytest

from girder.constants import AccessType, EDIT_METADATA_FLAG
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def readableFolder(admin, user):
    folder = Folder().createFolder(
        parent=admin, parentType='user', creator=admin, name='readable', public=False)
    Folder().setUserAccess(folder, user, AccessType.READ, save=True)
    item = Item().createItem('item', admin, folder)
    item = Item().setMetadata(item, {'existing': 'value'})
    yield {'folder': folder, 'item': item}


def _getItem(server, item, **kwargs):
    return server.request(path='/item/%s' % item['_id'], **kwargs)


def _setMetadata(server, item, metadata, **kwargs):
    return server.request(
        path='/item/%s/metadata' % item['_id'], method='PUT',
        body=json.dumps(metadata), type='application/json', **kwargs)


def _deleteMetadata(server, item, fields, **kwargs):
    return server.request(
        path='/item/%s/metadata' % item['_id'], method='DELETE',
        body=json.dumps(fields), type='application/json', **kwargs)


def _assertCanEditMetadata(server, item, user):
    resp = _getItem(server, item, user=user)
    assertStatusOk(resp)
    assert resp.json['_canEditMetadata'] is True

    resp = _setMetadata(server, item, {'foo': 'bar'}, user=user)
    assertStatusOk(resp)
    assert resp.json['meta'] == {'existing': 'value', 'foo': 'bar'}

    resp = _setMetadata(server, item, {'foo': 'baz'}, user=user)
    assertStatusOk(resp)
    assert resp.json['meta']['foo'] == 'baz'

    resp = server.request(
        path='/item/%s/metadata' % item['_id'], method='PUT', user=user,
        params={'allowNull': True}, body=json.dumps({'foo': None}), type='application/json')
    assertStatusOk(resp)
    assert resp.json['meta']['foo'] is None

    resp = _setMetadata(server, item, {'foo': None}, user=user)
    assertStatusOk(resp)
    assert 'foo' not in resp.json['meta']

    resp = _deleteMetadata(server, item, ['existing'], user=user)
    assertStatusOk(resp)
    assert resp.json['meta'] == {}


def testReadOnlyUserCannotEditMetadata(server, user, readableFolder):
    item = readableFolder['item']

    resp = _getItem(server, item, user=user)
    assertStatusOk(resp)
    assert resp.json['_canEditMetadata'] is False

    resp = _setMetadata(server, item, {'foo': 'bar'}, user=user)
    assertStatus(resp, 403)
    resp = _deleteMetadata(server, item, ['existing'], user=user)
    assertStatus(resp, 403)
    assert Item().load(item['_id'], force=True)['meta'] == {'existing': 'value'}


def testUserFlagAllowsMetadataEdit(server, user, readableFolder):
    Folder().setUserAccess(
        readableFolder['folder'], user, AccessType.READ, flags=[EDIT_METADATA_FLAG], save=True)
    _assertCanEditMetadata(server, readableFolder['item'], user)


def testGroupFlagAllowsMetadataEdit(server, admin, user, readableFolder):
    group = Group().createGroup('editors', admin)
    Group().addUser(group, user)
    Folder().setGroupAccess(
        readableFolder['folder'], group, AccessType.READ, flags=[EDIT_METADATA_FLAG], save=True)
    _assertCanEditMetadata(server, readableFolder['item'], user)


def testWriteAccessWithoutFlagAllowsMetadataEdit(server, user, readableFolder):
    Folder().setUserAccess(readableFolder['folder'], user, AccessType.WRITE, save=True)
    _assertCanEditMetadata(server, readableFolder['item'], user)


def testFlagDoesNotGrantOtherItemWrites(server, user, readableFolder):
    Folder().setUserAccess(
        readableFolder['folder'], user, AccessType.READ, flags=[EDIT_METADATA_FLAG], save=True)
    item = readableFolder['item']

    resp = server.request(
        path='/item/%s' % item['_id'], method='PUT', user=user,
        params={'name': 'renamed', 'metadata': json.dumps({'foo': 'bar'})})
    assertStatus(resp, 403)

    resp = server.request(path='/item/%s' % item['_id'], method='DELETE', user=user)
    assertStatus(resp, 403)

    item = Item().load(item['_id'], force=True)
    assert item['name'] == 'item'
    assert item['meta'] == {'existing': 'value'}


def testAnonymousCannotEditMetadata(server, readableFolder):
    folder = Folder().setPublic(readableFolder['folder'], True, save=True)
    Folder().setPublicFlags(folder, [EDIT_METADATA_FLAG], force=True, save=True)
    item = readableFolder['item']

    resp = _getItem(server, item)
    assertStatusOk(resp)
    assert resp.json['_canEditMetadata'] is False

    resp = _setMetadata(server, item, {'foo': 'bar'})
    assertStatus(resp, 401)
    resp = _deleteMetadata(server, item, ['existing'])
    assertStatus(resp, 401)


def testRecursiveFlagReachesSubfolderItems(server, admin, user, readableFolder):
    folder = readableFolder['folder']
    subfolder = Folder().createFolder(
        parent=folder, parentType='folder', creator=admin, name='sub')
    subitem = Item().createItem('subitem', admin, subfolder)

    resp = _setMetadata(server, subitem, {'foo': 'bar'}, user=user)
    assertStatus(resp, 403)

    Folder().setUserAccess(folder, user, AccessType.READ, flags=[EDIT_METADATA_FLAG])
    Folder().setAccessList(folder, folder['access'], save=True, recurse=True, user=admin)

    resp = _setMetadata(server, subitem, {'foo': 'bar'}, user=user)
    assertStatusOk(resp)
    assert resp.json['meta'] == {'foo': 'bar'}
