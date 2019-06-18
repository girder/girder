# -*- coding: utf-8 -*-
import collections
import pytest

from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User
from pytest_girder.assertions import assertStatus, assertStatusOk

Hierarchy = collections.namedtuple('Hierarchy', ['collections', 'folders', 'items', 'files'])


@pytest.fixture
def hierarchy(admin, fsAssetstore):
    c1 = Collection().createCollection(name='Coll1', creator=admin)
    c2 = Collection().createCollection(name='Coll2', creator=admin)
    f1 = Folder().createFolder(parent=c1, creator=admin, parentType='collection', name='Top level')
    f2 = Folder().createFolder(parent=f1, creator=admin, parentType='folder', name='Subfolder')
    i1 = Item().createItem(name='Item1', creator=admin, folder=f1)
    i2 = Item().createItem(name='Item10', creator=admin, folder=f2)
    file1 = File().createFile(
        name='File1', creator=admin, item=i1, size=1, assetstore=fsAssetstore, mimeType='text/csv')
    file2 = File().createFile(
        name='File2', creator=admin, item=i2, size=10, assetstore=fsAssetstore, mimeType='text/csv')

    yield Hierarchy(collections=(c1, c2), folders=(f1, f2), items=(i1, i2), files=(file1, file2))


def assertNodeSize(resource, model, size):
    __tracebackhide__ = True
    model = model().load(resource['_id'], force=True)
    assert model['size'] == size


def testMoveItemToSubfolder(server, admin, hierarchy):
    assertNodeSize(hierarchy.items[0], Item, 1)
    assertNodeSize(hierarchy.items[1], Item, 10)
    assertNodeSize(hierarchy.folders[0], Folder, 1)
    assertNodeSize(hierarchy.folders[1], Folder, 10)
    assertNodeSize(hierarchy.collections[0], Collection, 11)

    resp = server.request(
        path='/item/%s' % hierarchy.items[0]['_id'], method='PUT',
        user=admin, params={
            'folderId': hierarchy.folders[1]['_id']
        })
    assertStatusOk(resp)
    assertNodeSize(hierarchy.items[0], Item, 1)
    assertNodeSize(hierarchy.items[1], Item, 10)
    assertNodeSize(hierarchy.folders[0], Folder, 0)
    assertNodeSize(hierarchy.folders[1], Folder, 11)
    assertNodeSize(hierarchy.collections[0], Collection, 11)


def testDeleteItemUpdatesSize(server, admin, hierarchy):
    resp = server.request(path='/item/%s' % hierarchy.items[0]['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)

    assertNodeSize(hierarchy.folders[0], Folder, 0)
    assertNodeSize(hierarchy.folders[1], Folder, 10)
    assertNodeSize(hierarchy.collections[0], Collection, 10)


def testMoveFolderUnderItselfFails(server, admin, hierarchy):
    resp = server.request(
        path='/folder/%s' % hierarchy.folders[0]['_id'], method='PUT',
        user=admin, params={
            'parentId': hierarchy.folders[1]['_id'],
            'parentType': 'folder'
        })
    assertStatus(resp, 400)
    assert resp.json['message'] == 'You may not move a folder underneath itself.'


def testMoveFolderToNewCollection(server, admin, hierarchy):
    assertNodeSize(hierarchy.collections[0], Collection, 11)
    assertNodeSize(hierarchy.collections[1], Collection, 0)

    resp = server.request(
        path='/folder/%s' % hierarchy.folders[0]['_id'], method='PUT',
        user=admin, params={
            'parentId': hierarchy.collections[1]['_id'],
            'parentType': 'collection'
        })
    assertStatusOk(resp)
    assertNodeSize(hierarchy.collections[0], Collection, 0)
    assertNodeSize(hierarchy.collections[1], Collection, 11)


def testMoveSubfolderToUser(server, admin, hierarchy):
    resp = server.request(
        path='/folder/%s' % hierarchy.folders[1]['_id'], method='PUT',
        user=admin, params={
            'parentId': admin['_id'],
            'parentType': 'user'
        })
    assertStatusOk(resp)
    assertNodeSize(admin, User, 10)
    assertNodeSize(hierarchy.collections[0], Collection, 1)


def testDeleteFolderUpdatesSize(server, admin, hierarchy):
    resp = server.request(
        path='/folder/%s' % hierarchy.folders[1]['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assertNodeSize(hierarchy.collections[0], Collection, 1)
