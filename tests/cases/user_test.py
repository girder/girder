#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import cherrypy
import json

from .. import base

from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class UserTestCase(base.TestCase):

    def _verifyAuthCookie(self, resp):
        self.assertTrue('authToken' in resp.cookie)
        cookieVal = json.loads(resp.cookie['authToken'].value)
        self.assertHasKeys(cookieVal, ['token', 'userId'])
        self.assertEqual(
            resp.cookie['authToken']['expires'],
            cherrypy.config['sessions']['cookie_lifetime'] * 3600 * 24)

    def _verifyUserDocument(self, doc, admin=True):
        self.assertHasKeys(
            doc, ['_id', 'firstName', 'lastName', 'public', 'login', 'admin'])
        if admin:
            self.assertHasKeys(doc, ['email', 'size'])
        else:
            self.assertNotHasKeys(doc, ['access', 'email', 'size'])

        self.assertNotHasKeys(doc, ['salt'])

    def testRegisterAndLoginBcrypt(self):
        """
        Test user registration and logging in.
        """
        cherrypy.config['auth']['hash_alg'] = 'bcrypt'
        # Set this to minimum so test runs faster.
        cherrypy.config['auth']['bcrypt_rounds'] = 4

        params = {
            'email': 'bad_email',
            'login': 'illegal@login',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'bad'
        }
        # First test all of the required parameters.
        self.ensureRequiredParams(
            path='/user', method='POST', required=params.keys())

        # Now test parameter validation
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'password')
        self.assertEqual(cherrypy.config['users']['password_description'],
                         resp.json['message'])

        params['password'] = 'goodpassword'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')

        # Make login something that violates the regex but doesn't contain @
        params['login'] = ' '
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')
        self.assertEqual(cherrypy.config['users']['login_description'],
                         resp.json['message'])

        params['login'] = 'goodlogin'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'email')

        # Now successfully create the user
        params['email'] = 'good@email.com'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)

        user = self.model('user').load(resp.json['_id'], force=True)
        self.assertEqual(user['hashAlg'], 'bcrypt')

        # Now that our user is created, try to login
        params = {
            'login': 'incorrect@email.com',
            'password': 'badpassword'
        }
        self.ensureRequiredParams(
            path='/user/login', method='POST', required=params.keys())

        # Login with unregistered email
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Correct email, but wrong password
        params['login'] = 'good@email.com'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with email
        params['password'] = 'goodpassword'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ['authToken'])
        self.assertHasKeys(
            resp.json['authToken'], ['token', 'expires', 'userId'])

        # Invalid login
        params['login'] = 'badlogin'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with login
        params['login'] = 'goodlogin'
        resp = self.request(path='/user/login', method='POST', params=params)
        self.assertStatusOk(resp)

        # Make sure we got a nice cookie
        self._verifyAuthCookie(resp)

    def testRegisterAndLoginSha512(self):
        cherrypy.config['auth']['hash_alg'] = 'sha512'

        params = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }

        # Register a user with sha512 storage backend
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)

        user = self.model('user').load(resp.json['_id'], force=True)
        self.assertEqual(user['hashAlg'], 'sha512')

        # Login unsuccessfully
        resp = self.request(path='/user/login', method='POST', params={
            'login': params['login'],
            'password': params['password'] + '.'
            })
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully
        resp = self.request(path='/user/login', method='POST', params={
            'login': params['login'],
            'password': params['password']
            })
        self.assertStatusOk(resp)
        self.assertEqual('Login succeeded.', resp.json['message'])
        self.assertEqual('good@email.com', resp.json['user']['email'])
        self._verifyUserDocument(resp.json['user'])

        # Make sure we got a nice cookie
        self._verifyAuthCookie(resp)

    def testGetUser(self):
        """
        Tests for the GET user endpoint.
        """
        params = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
            }
        user = self.model('user').createUser(**params)
        resp = self.request(path='/user/%s' % user['_id'])
        self._verifyUserDocument(resp.json, admin=False)

    def testDeleteUser(self):
        """
        Test the behavior of deleting users.
        """
        # Create a couple of users
        users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

        # Create a folder and give both users some access on it
        folder = self.model('folder').createFolder(
            parent=users[0], name='x', parentType='user', public=False,
            creator=users[0])
        self.model('folder').setUserAccess(folder, users[0], AccessType.WRITE)
        self.model('folder').setUserAccess(folder, users[1], AccessType.READ)
        folder = self.model('folder').save(folder)

        self.assertEqual(len(folder['access']['users']), 2)

        token = self.model('token').createToken(users[1])

        # Make sure non-admin users can't delete other users
        resp = self.request(path='/user/%s' % users[0]['_id'], method='DELETE',
                            user=users[1])
        self.assertStatus(resp, 403)

        # Delete user 1 as admin, should work
        resp = self.request(path='/user/%s' % users[1]['_id'], method='DELETE',
                            user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(
            resp.json['message'], 'Deleted user %s.' % users[1]['login'])

        users[1] = self.model('user').load(users[1]['_id'], force=True)
        folder = self.model('folder').load(folder['_id'], force=True)
        token = self.model('token').load(token['_id'], force=True,
                                         objectId=False)

        # Make sure user and token were deleted
        self.assertEqual(users[1], None)
        self.assertEqual(token, None)

        # Make sure access control references for the user were deleted
        self.assertEqual(len(folder['access']['users']), 1)

        # Delete user 0
        resp = self.request(path='/user/%s' % users[0]['_id'], method='DELETE',
                            user=users[0])
        self.assertStatusOk(resp)

        # Make sure the user's folder was deleted
        folder = self.model('folder').load(folder['_id'], force=True)
        self.assertEqual(folder, None)

    def testUserIndex(self):
        """
        Test user list endpoint.
        """
        # Create some users.
        users = [self.model('user').createUser(
            'usr%s' % x, 'passwd', 'tst', '%s_usr' % x, 'u%s@u.com' % x)
            for x in ['c', 'a', 'b']]
        resp = self.request(path='/user', method='GET', params={
            'limit': 2,
            'offset': 1
            })
        self.assertStatusOk(resp)

        # Make sure the limit, order, and offset are respected, and that our
        # default sorting is by lastName.
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['lastName'], 'b_usr')
        self.assertEqual(resp.json[1]['lastName'], 'c_usr')
