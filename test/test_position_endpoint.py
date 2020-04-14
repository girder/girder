# -*- coding: utf-8 -*-
import pytest

from girder.models.item import Item
from girder.models.folder import Folder
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def makeResources(admin):
    publicFolder = Folder().findOne({'parentId': admin['_id'], 'name': 'Public'})
    folders = []
    publicItems = []
    privateItems = []
    for i in range(20):
        folder = Folder().createFolder(
            parent=publicFolder, creator=admin, parentType='folder', name='Folder %d' % i)
        if i % 2:
            folder = Folder().setPublic(folder, False, save=True)
        folders.append(folder)
    for i in range(20):
        publicItems.append(Item().createItem(
            name='Public Item %d' % i, creator=admin, folder=folders[0]))
        privateItems.append(Item().createItem(
            name='Private Item %d' % i, creator=admin, folder=folders[1]))
    yield {
        'publicFolder': publicFolder,
        'folders': folders,
        'publicItems': publicItems,
        'privateItems': privateItems,
    }


def testFolderPosition(server, makeResources, admin):
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][10]['_id']),
        user=admin,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id'])
        })
    assertStatusOk(resp)
    # alphabetical by C sort
    assert resp.json == 2


def testFolderPosition7(server, makeResources, admin):
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][7]['_id']),
        user=admin,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id'])
        })
    assertStatusOk(resp)
    assert resp.json == 17


def testFolderPositionWithSearchNotPresent(server, makeResources, admin):
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][7]['_id']),
        user=admin,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id']),
            'text': '"Folder 1"',
        })
    assertStatusOk(resp)
    assert resp.json == 11


def testFolderPositionUser(server, makeResources, user):
    # A user only sees public folders
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][10]['_id']),
        user=user,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id'])
        })
    assertStatusOk(resp)
    assert resp.json == 1


def testFolderPositionUserNoAccess(server, makeResources, user):
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][7]['_id']),
        user=user,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id'])
        })
    assertStatus(resp, 403)


def testFolderPositionWithSearchPresent(server, makeResources, admin):
    resp = server.request(
        '/folder/%s/position' % str(makeResources['folders'][16]['_id']),
        user=admin,
        params={
            'parentType': 'folder',
            'parentId': str(makeResources['publicFolder']['_id']),
            'text': '"Folder 1"',
        })
    assertStatusOk(resp)
    assert resp.json == 7


def testItemPosition(server, makeResources, admin):
    resp = server.request(
        '/item/%s/position' % str(makeResources['publicItems'][10]['_id']),
        user=admin,
        params={
            'folderId': str(makeResources['folders'][0]['_id'])
        })
    assertStatusOk(resp)
    assert resp.json == 2


def testItemPosition7(server, makeResources, admin):
    resp = server.request(
        '/item/%s/position' % str(makeResources['privateItems'][7]['_id']),
        user=admin,
        params={
            'folderId': str(makeResources['folders'][1]['_id'])
        })
    assertStatusOk(resp)
    assert resp.json == 17


def testItemPositionWithSearchNotPresent(server, makeResources, admin):
    resp = server.request(
        '/item/%s/position' % str(makeResources['publicItems'][7]['_id']),
        user=admin,
        params={
            'folderId': str(makeResources['folders'][0]['_id']),
            'text': '"Item 1"',
        })
    assertStatusOk(resp)
    assert resp.json == 11


def testItemPositionUser(server, makeResources, user):
    # A user only sees public folders
    resp = server.request(
        '/item/%s/position' % str(makeResources['publicItems'][10]['_id']),
        user=user,
        params={
            'folderId': str(makeResources['folders'][0]['_id'])
        })
    assertStatusOk(resp)
    assert resp.json == 2


def testItemPositionUserNoAccess(server, makeResources, user):
    resp = server.request(
        '/item/%s/position' % str(makeResources['privateItems'][7]['_id']),
        user=user,
        params={
            'folderId': str(makeResources['folders'][1]['_id'])
        })
    assertStatus(resp, 403)


def testItemPositionUserSearch(server, makeResources, user):
    resp = server.request(
        '/item/%s/position' % str(makeResources['publicItems'][7]['_id']),
        user=user,
        params={
            'folderId': str(makeResources['folders'][0]['_id']),
            'text': '"Item 1"',
        })
    assertStatusOk(resp)
    assert resp.json == 11
