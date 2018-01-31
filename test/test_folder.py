#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import pytest
from bson.objectid import ObjectId

from girder.exceptions import AccessException
from girder.models.folder import Folder
from pytest_girder.assertions import assertStatus, assertStatusOk

def _createParentChain(admin):
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
    return F1, F2, privateFolder, F4


def testParentsToRoot(admin, user):
    """
    Demonstrate that parentsToRoot works even if the user has missing right access
    on one or more folder in the full path.
    This tests for a user with right access, a user without and a none user.
    """
    # Create the parent chain
    F1, F2, privateFolder, F4 = _createParentChain(admin)

    # Get the parent chain for a user who has access rights
    parents = Folder().parentsToRoot(F4, user=admin)
    for idx in range(1, 4):
        assert parents[idx]['object']['name'] == 'F%i' % idx

    # Get the parent chain for a user who doesn't have access rights
    with pytest.raises(AccessException):
        parents = Folder().parentsToRoot(F4, user=user)
        for idx in range(1, 4):
            if idx == 3:
                assert parents[idx] is None
            else:
                assert parents[idx]['object']['name'] == 'F%i' % idx

    # Get the parent chain for a none user
    with pytest.raises(AccessException):
        parents = Folder().parentsToRoot(F4, user=None)
        for idx in range(1, 4):
            if idx == 3:
                assert parents[idx] is None
            else:
                assert parents[idx]['object']['name'] == 'F%i' % idx


def testGetResourceByPath(server, admin, user):
    # Create the parent chain
    F1, F2, privateFolder, F4 = _createParentChain(admin)
    # Test access denied response for access 'hidden folder' for user with access rights,
    # user without and none user
    resp = server.request(path='/resource/lookup',
                          method='GET', user=admin,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  F1['name'],
                                  F2['name'],
                                  privateFolder['name'],
                                  F4['name'])
                          })
    assertStatusOk(resp)
    assert resp.json['name'] == F4['name']
    assert ObjectId(resp.json['_id']) == F4['_id']
    resp = server.request(path='/resource/lookup',
                          method='GET', user=user,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  F1['name'],
                                  F2['name'],
                                  privateFolder['name'],
                                  F4['name'])
                          })
    assertStatus(resp, 400)
    resp = server.request(path='/resource/lookup',
                          method='GET', user=None,
                          params={
                              'path': '/user/%s/%s/%s/%s/%s' % (
                                  admin['login'],
                                  F1['name'],
                                  F2['name'],
                                  privateFolder['name'],
                                  F4['name'])
                          })
    assertStatus(resp, 400)


def testGetResourcePath(server, admin, user):
    # Create the parent chain
    F1, F2, privateFolder, F4 = _createParentChain(admin)
    # Test access denied response for access 'hidden folder' for user with access rights,
    # user without and none user
    resp = server.request(path='/resource/%s/path' % F4['_id'],
                          method='GET', user=admin,
                          params={'type': 'folder'})
    assertStatusOk(resp)
    assert resp.json == '/user/%s/%s/%s/%s/%s' % (
        admin['login'], F1['name'], F2['name'], privateFolder['name'], F4['name'])
    resp = server.request(path='/resource/%s/path' % F4['_id'],
                          method='GET', user=user,
                          params={'type': 'folder'})
    assertStatus(resp, 403)
    resp = server.request(path='/resource/%s/path' % F4['_id'],
                          method='GET', user=None,
                          params={'type': 'folder'})
    assertStatus(resp, 401)
