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

from .. import base

from girder.api.rest import loadmodel, Resource
from girder.api import access
from girder.constants import AccessType, SettingKey, TokenScope


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


def setUpModule():
    server = base.startServer()
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


def tearDownModule():
    base.stopServer()


class AccessTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        admin = {
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': u'Admin\ua000',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = self.model('user').createUser(**user)

    def testAccessEndpoints(self):
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
            resp = self.request(path=endpoint[0], method='GET', user=None)
            if endpoint[1] in ("public", ):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 401)
            resp = self.request(path=endpoint[0], method='GET', user=self.user)
            if endpoint[1] in ("public", "user"):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 403)
            resp = self.request(path=endpoint[0], method='GET', user=self.admin)
            if endpoint[1] in ("public", "user", "admin"):
                self.assertStatusOk(resp)
            else:
                self.assertStatus(resp, 403)

    def testCookieAuth(self):
        # No auth should always be rejected
        for decorator in ['cookie_auth', 'cookie_force_auth']:
            for method in ['GET', 'POST']:
                resp = self.request(path='/accesstest/%s' % decorator,
                                    method=method)
                self.assertStatus(resp, 401)

        # Token auth should always still succeed
        for decorator in ['cookie_auth', 'cookie_force_auth']:
            for method in ['GET', 'POST']:
                resp = self.request(path='/accesstest/%s' % decorator,
                                    method=method, user=self.user)
                self.assertStatusOk(resp)

        # Cookie auth should succeed unless POSTing to non-force endpoint
        cookie = 'girderToken=%s' % self._genToken(self.user)
        for decorator in ['cookie_auth', 'cookie_force_auth']:
            for method in ['GET', 'POST']:
                resp = self.request(path='/accesstest/%s' % decorator,
                                    method=method, cookie=cookie)
                if decorator == 'cookie_auth' and method != 'GET':
                    self.assertStatus(resp, 401)
                else:
                    self.assertStatusOk(resp)

    def testLoadModelDecorator(self):
        resp = self.request(
            path='/accesstest/test_loadmodel_plain/%s' % self.user['_id'], method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], str(self.user['_id']))

        resp = self.request(path='/accesstest/test_loadmodel_query', params={'userId': None})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid ObjectId: None')

    def testGetFullAccessList(self):
        acl = self.model('user').getFullAccessList(self.admin)
        self.assertEqual(len(acl['users']), 1)

    def testAdminTokenScopes(self):
        adminSettingToken = self.model('token').createToken(
            user=self.admin, scope=TokenScope.SETTINGS_READ)
        adminEmailToken = self.model('token').createToken(
            user=self.admin, scope=TokenScope.DATA_READ)
        nonadminToken = self.model('token').createToken(
            user=self.user, scope=TokenScope.SETTINGS_READ)

        # Reading settings as admin should work
        params = {'key': SettingKey.SMTP_PORT}
        path = '/system/setting'
        resp = self.request(path=path, params=params, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 25)

        # Reading setting as non-admin should fail
        resp = self.request(path=path, params=params, user=self.user)
        self.assertStatus(resp, 403)

        # Reading settings with a properly scoped token should work
        resp = self.request(path=path, params=params, token=adminSettingToken)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 25)

        # Reading settings with an improperly scoped token should fail
        resp = self.request(path=path, params=params, token=adminEmailToken)
        self.assertStatus(resp, 401)

        # Non-admin user with this token scope should still not work
        resp = self.request(path=path, params=params, token=nonadminToken)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Administrator access required.')

        # The setting-scope token should not grant access to other endpoints
        resp = self.request(path='/assetstore', token=adminSettingToken)
        self.assertStatus(resp, 401)

    def testArtificialScopedAccess(self):
        # Make sure raw decorator is equivalent to returned decorator.
        resp = self.request(path='/accesstest/admin_access', user=self.admin)
        self.assertStatusOk(resp)

        resp = self.request(path='/accesstest/admin_access', user=self.user)
        self.assertStatus(resp, 403)

        resp = self.request(path='/accesstest/fn_admin', user=self.admin)
        self.assertStatusOk(resp)

        resp = self.request(path='/accesstest/fn_admin', user=self.user)
        self.assertStatus(resp, 403)

        token = self.model('token').createToken(
            user=self.admin, scope=TokenScope.SETTINGS_READ)

        resp = self.request(path='/accesstest/admin_access', token=token)
        self.assertStatus(resp, 401)

        resp = self.request(path='/accesstest/fn_admin', token=token)
        self.assertStatus(resp, 401)

        # Make sure user scoped access works
        token = self.model('token').createToken(
            user=self.user, scope=TokenScope.DATA_READ)

        resp = self.request(path='/accesstest/user_access', user=self.user)
        self.assertStatusOk(resp)

        resp = self.request(path='/accesstest/scoped_user', user=self.user)
        self.assertStatusOk(resp)

        resp = self.request(path='/accesstest/user_access', token=token)
        self.assertStatus(resp, 401)

        resp = self.request(path='/accesstest/scoped_user', token=token)
        self.assertStatusOk(resp)

        # Test public access
        authToken = self.model('token').createToken(user=self.user)

        for route in ('public_access', 'fn_public', 'scoped_public'):
            path = '/accesstest/%s' % route

            for t in (token, None):
                resp = self.request(path=path, token=t)
                self.assertStatusOk(resp)
                self.assertEqual(resp.json, None)

            resp = self.request(path=path, token=authToken)
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['_id'], str(self.user['_id']))

        # Make a correctly scoped token, should work.
        token = self.model('token').createToken(
            user=self.user, scope=TokenScope.SETTINGS_READ)
        resp = self.request(path=path, token=token)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], str(self.user['_id']))
