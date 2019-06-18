# -*- coding: utf-8 -*-
import pytest
from bson.objectid import ObjectId

from girder.exceptions import AccessException
from girder.models.folder import Folder
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def parentChain(admin):
    # Create the parent chain
    F1 = Folder().createFolder(
        parent=admin, parentType='user', creator=admin,
        name='F1', public=True)
    F2 = Folder().createFolder(
        parent=F1, parentType='folder', creator=admin,
        name='F2', public=True)
    privateFolder = Folder().createFolder(
        parent=F2, parentType='folder', creator=admin,
        name='F3', public=False)
    F4 = Folder().createFolder(
        parent=privateFolder, parentType='folder', creator=admin,
        name='F4', public=True)
    yield {
        'folder1': F1,
        'folder2': F2,
        'privateFolder': privateFolder,
        'folder4': F4
    }


def testParentsToRootAdmin(parentChain, admin):
    # Get the parent chain for a user who has access rights
    parents = Folder().parentsToRoot(parentChain['folder4'], user=admin)
    assert parents[1]['object']['name'] == 'F1'
    assert parents[2]['object']['name'] == 'F2'
    assert parents[3]['object']['name'] == 'F3'


def testParentsToRootNoRights(parentChain, user):
    # Get the parent chain for a user who doesn't have access rights
    with pytest.raises(AccessException):
        parents = Folder().parentsToRoot(parentChain['folder4'], user=user)
        assert parents[1]['object']['name'] == 'F1'
        assert parents[2]['object']['name'] == 'F2'
        assert parents[3] is None


def testParentsToRootNoUsers(parentChain):
    # Get the parent chain for a none user
    with pytest.raises(AccessException):
        parents = Folder().parentsToRoot(parentChain['folder4'], user=None)
        assert parents[1]['object']['name'] == 'F1'
        assert parents[2]['object']['name'] == 'F2'
        assert parents[3] is None


def testGetResourceByPathForAdmin(server, parentChain, admin):
    # Test access denied response for access 'hidden folder' for user with access rights
    resp = server.request(path='/resource/lookup',
                          method='GET', user=admin,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  parentChain['folder1']['name'],
                                  parentChain['folder2']['name'],
                                  parentChain['privateFolder']['name'],
                                  parentChain['folder4']['name'])
                          })
    assertStatusOk(resp)
    assert resp.json['name'] == parentChain['folder4']['name']
    assert ObjectId(resp.json['_id']) == parentChain['folder4']['_id']


def testGetResourceByPathForUser(server, parentChain, admin, user):
    # Test access denied response for access 'hidden folder' for user without access rights
    resp = server.request(path='/resource/lookup',
                          method='GET', user=user,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  parentChain['folder1']['name'],
                                  parentChain['folder2']['name'],
                                  parentChain['privateFolder']['name'],
                                  parentChain['folder4']['name'])
                          })
    assertStatus(resp, 400)


def testGetResourceByPathForNoneUser(server, parentChain, admin):
    # Test access denied response for access 'hidden folder' for a none user
    resp = server.request(path='/resource/lookup',
                          method='GET', user=None,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  parentChain['folder1']['name'],
                                  parentChain['folder2']['name'],
                                  parentChain['privateFolder']['name'],
                                  parentChain['folder4']['name'])
                          })
    assertStatus(resp, 400)


def testGetResourcePathForAdmin(server, parentChain, admin):
    # Test access denied response for access 'hidden folder' for user with access rights
    resp = server.request(path='/resource/%s/path' % parentChain['folder4']['_id'],
                          method='GET', user=admin,
                          params={'type': 'folder'})
    assertStatusOk(resp)
    assert resp.json == '/user/%s/%s/%s/%s/%s' % (
        admin['login'],
        parentChain['folder1']['name'],
        parentChain['folder2']['name'],
        parentChain['privateFolder']['name'],
        parentChain['folder4']['name'])


def testGetResourcePathForUser(server, parentChain, user):
    # Test access denied response for access 'hidden folder' for user without access rights
    resp = server.request(path='/resource/%s/path' % parentChain['folder4']['_id'],
                          method='GET', user=user,
                          params={'type': 'folder'})
    assertStatus(resp, 403)


def testGetResourcePathForNoneUser(server, parentChain):
    # Test access denied response for access 'hidden folder' for a none User
    resp = server.request(path='/resource/%s/path' % parentChain['folder4']['_id'],
                          method='GET', user=None,
                          params={'type': 'folder'})
    assertStatus(resp, 401)
