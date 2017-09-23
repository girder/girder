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

from girder.api.rest import loadmodel, Resource
from girder.api import access
from girder.constants import AccessType, SettingKey, TokenScope
from girder.models.user import User
from girder.models.token import Token
from pytest_girder.assertions import assertStatus, assertStatusOk


CUSTOM_SCOPE = "Some.Exclusive.Scope"


# We deliberately don't have an access decorator
def defaultFunctionHandler(**kwargs):
    return


@access.admin
def adminFunctionHandler(**kwargs):
    return


@access.user
def userFunctionHandler(**kwargs):
    return


@access.public
def publicFunctionHandler(**kwargs):
    return


@access.token(scope=CUSTOM_SCOPE, required=True)
def requireScope(**kwargs):
    return


@access.public
@loadmodel(map={'id': 'user'}, model='user', level=AccessType.READ)
def plainFn(user, params):
    return user


@access.public
@loadmodel(map={'userId': 'user'}, model='user', level=AccessType.READ)
def loadModelWithMap(user, params):
    return user


class AccessTestResource(Resource):
    def __init__(self):
        super(AccessTestResource, self).__init__()
        self.resourceName = 'accesstest'
        self.route('GET', ('default_access', ), self.defaultHandler)
        self.route('GET', ('admin_access', ), self.adminHandler)
        self.route('GET', ('user_access', ), self.userHandler)
        self.route('GET', ('public_access', ), self.publicHandler)
        self.route('GET', ('cookie_auth', ), self.cookieHandler)
        self.route('POST', ('cookie_auth', ), self.cookieHandler)
        self.route('GET', ('cookie_force_auth', ), self.cookieForceHandler)
        self.route('POST', ('cookie_force_auth', ), self.cookieForceHandler)
        self.route('GET', ('fn_admin', ), self.fnAdmin)
        self.route('GET', ('scoped_user', ), self.scopedUser)
        self.route('GET', ('fn_public', ), self.fnPublic)
        self.route('GET', ('scoped_public', ), self.scopedPublic)

    # We deliberately don't have an access decorator
    def defaultHandler(self, **kwargs):
        return

    @access.admin
    def adminHandler(self, **kwargs):
        return

    @access.user
    def userHandler(self, **kwargs):
        return

    @access.public
    def publicHandler(self, **kwargs):
        return self.getCurrentUser()

    @access.cookie
    @access.user
    def cookieHandler(self, **kwargs):
        return

    @access.cookie(force=True)
    @access.user
    def cookieForceHandler(self, **kwargs):
        return

    @access.admin()
    def fnAdmin(self, **kwargs):
        return

    @access.user(scope=TokenScope.DATA_READ)
    def scopedUser(self, **kwargs):
        return

    @access.public()
    def fnPublic(self, **kwargs):
        return self.getCurrentUser()

    @access.public(scope=TokenScope.SETTINGS_READ)
    def scopedPublic(self, **kwargs):
        return self.getCurrentUser()


@pytest.fixture
def server(server):
    server.root.api.v1.accesstest = AccessTestResource()
    # Public access endpoints do not need to be a Resource subclass method,
    # they can be a regular function
    accesstest = server.root.api.v1.accesstest
    accesstest.route('GET', ('default_function_access', ),
                     defaultFunctionHandler)
    accesstest.route('GET', ('admin_function_access', ), adminFunctionHandler)
    accesstest.route('GET', ('user_function_access', ), userFunctionHandler)
    accesstest.route('GET', ('public_function_access', ),
                     publicFunctionHandler)
    accesstest.route('GET', ('test_loadmodel_plain', ':id'), plainFn)
    accesstest.route('GET', ('test_loadmodel_query',), loadModelWithMap)
    accesstest.route('GET', ('test_required_scope_exists', ), requireScope)

    yield server


def testAccessEndpoints(server, admin, user):
    endpoints = [
        ("/accesstest/default_access", "admin"),
        ("/accesstest/admin_access", "admin"),
        ("/accesstest/user_access", "user"),
        ("/accesstest/public_access", "public"),
        ("/accesstest/default_function_access", "admin"),
        ("/accesstest/admin_function_access", "admin"),
        ("/accesstest/user_function_access", "user"),
        ("/accesstest/public_function_access", "public"),
    ]
    for endpoint in endpoints:
        resp = server.request(path=endpoint[0], method='GET', user=None)
        if endpoint[1] in ("public", ):
            assertStatusOk(resp)
        else:
            assertStatus(resp, 401)
        resp = server.request(path=endpoint[0], method='GET', user=user)
        if endpoint[1] in ("public", "user"):
            assertStatusOk(resp)
        else:
            assertStatus(resp, 403)
        resp = server.request(path=endpoint[0], method='GET', user=admin)
        if endpoint[1] in ("public", "user", "admin"):
            assertStatusOk(resp)
        else:
            assertStatus(resp, 403)


def testCookieAuth(server, user):
    # No auth should always be rejected
    for decorator in ['cookie_auth', 'cookie_force_auth']:
        for method in ['GET', 'POST']:
            resp = server.request(path='/accesstest/%s' % decorator,
                                  method=method)
            assertStatus(resp, 401)

    # Token auth should always still succeed
    for decorator in ['cookie_auth', 'cookie_force_auth']:
        for method in ['GET', 'POST']:
            resp = server.request(path='/accesstest/%s' % decorator,
                                  method=method, user=user)
            assertStatusOk(resp)

    # Cookie auth should succeed unless POSTing to non-force endpoint
    cookie = 'girderToken=%s' % str(Token().createToken(user)['_id'])
    for decorator in ['cookie_auth', 'cookie_force_auth']:
        for method in ['GET', 'POST']:
            resp = server.request(path='/accesstest/%s' % decorator,
                                  method=method, cookie=cookie)
            if decorator == 'cookie_auth' and method != 'GET':
                assertStatus(resp, 401)
            else:
                assertStatusOk(resp)


def testLoadModelDecorator(server, user):
    resp = server.request(
        path='/accesstest/test_loadmodel_plain/%s' % user['_id'], method='GET')
    assertStatusOk(resp)
    assert resp.json['_id'] == str(user['_id'])

    resp = server.request(path='/accesstest/test_loadmodel_query', params={'userId': None})
    assertStatus(resp, 400)
    assert resp.json['message'] == 'Invalid ObjectId: None'


def testGetFullAccessList(db, admin):
    acl = User().getFullAccessList(admin)
    assert len(acl['users']) == 1


def testAdminTokenScopes(server, admin, user):
    adminSettingToken = Token().createToken(
        user=admin, scope=TokenScope.SETTINGS_READ)
    adminEmailToken = Token().createToken(
        user=admin, scope=TokenScope.DATA_READ)
    nonadminToken = Token().createToken(
        user=user, scope=TokenScope.SETTINGS_READ)

    # Reading settings as admin should work
    params = {'key': SettingKey.SMTP_PORT}
    path = '/system/setting'
    resp = server.request(path=path, params=params, user=admin)
    assertStatusOk(resp)
    assert resp.json == 25

    # Reading setting as non-admin should fail
    resp = server.request(path=path, params=params, user=user)
    assertStatus(resp, 403)

    # Reading settings with a properly scoped token should work
    resp = server.request(path=path, params=params, token=adminSettingToken)
    assertStatusOk(resp)
    assert resp.json == 25

    # Reading settings with an improperly scoped token should fail
    resp = server.request(path=path, params=params, token=adminEmailToken)
    assertStatus(resp, 401)

    # Non-admin user with this token scope should still not work
    resp = server.request(path=path, params=params, token=nonadminToken)
    assertStatus(resp, 403)
    assert resp.json['message'] == 'Administrator access required.'

    # The setting-scope token should not grant access to other endpoints
    resp = server.request(path='/assetstore', token=adminSettingToken)
    assertStatus(resp, 401)


def testArtificialScopedAccess(server, admin, user):
    # Make sure raw decorator is equivalent to returned decorator.
    resp = server.request(path='/accesstest/admin_access', user=admin)
    assertStatusOk(resp)

    resp = server.request(path='/accesstest/admin_access', user=user)
    assertStatus(resp, 403)

    resp = server.request(path='/accesstest/fn_admin', user=admin)
    assertStatusOk(resp)

    resp = server.request(path='/accesstest/fn_admin', user=user)
    assertStatus(resp, 403)

    token = Token().createToken(
        user=admin, scope=TokenScope.SETTINGS_READ)

    resp = server.request(path='/accesstest/admin_access', token=token)
    assertStatus(resp, 401)

    resp = server.request(path='/accesstest/fn_admin', token=token)
    assertStatus(resp, 401)

    # Make sure user scoped access works
    token = Token().createToken(
        user=user, scope=TokenScope.DATA_READ)

    resp = server.request(path='/accesstest/user_access', user=user)
    assertStatusOk(resp)

    resp = server.request(path='/accesstest/scoped_user', user=user)
    assertStatusOk(resp)

    resp = server.request(path='/accesstest/user_access', token=token)
    assertStatus(resp, 401)

    resp = server.request(path='/accesstest/scoped_user', token=token)
    assertStatusOk(resp)

    # Test public access
    authToken = Token().createToken(user=user)

    for route in ('public_access', 'fn_public', 'scoped_public'):
        path = '/accesstest/%s' % route

        for t in (token, None):
            resp = server.request(path=path, token=t)
            assertStatusOk(resp)
            assert resp.json is None

        resp = server.request(path=path, token=authToken)
        assertStatusOk(resp)
        assert resp.json['_id'] == str(user['_id'])

    # Make a correctly scoped token, should work.
    token = Token().createToken(
        user=user, scope=TokenScope.SETTINGS_READ)
    resp = server.request(path=path, token=token)
    assertStatusOk(resp)
    assert resp.json['_id'] == str(user['_id'])


def testRequiredScopeExists(server, user):
    token = Token().createToken(scope=CUSTOM_SCOPE)

    resp = server.request(path='/accesstest/test_required_scope_exists')
    # If not given a user or a valid auth token the status should be 401
    assertStatus(resp, 401)

    resp2 = server.request(path='/accesstest/test_required_scope_exists',
                           user=user)
    # If the token does not have the CUSTOM_SCOPE the status should be 403
    assertStatus(resp2, 403)

    # If user is not given but the token has the correct scope
    # the status should be 200
    resp3 = server.request(path='/accesstest/test_required_scope_exists',
                           token=token)

    assertStatus(resp3, 200)
