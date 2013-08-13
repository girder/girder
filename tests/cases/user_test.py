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

def setUpModule():
    base.startServer()

def tearDownModule():
    base.stopServer()

class UserTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        self.requireModels(['user'])

    def _verifyAuthCookie(self, resp):
        self.assertTrue(resp.cookie.has_key('authToken'))
        cookieVal = json.loads(resp.cookie['authToken'].value)
        self.assertHasKeys(cookieVal, ['token', 'userId'])
        self.assertEqual(resp.cookie['authToken']['expires'],
                         cherrypy.config['sessions']['cookie_lifetime'] * 3600 * 24)

    def _verifyUserDocument(self, doc):
        self.assertHasKeys(doc, ['_id', 'firstName', 'lastName', 'email', 'login',
                                       'admin', 'size', 'hashAlg'])
        self.assertNotHasKeys(doc, ['salt'])

    def testRegisterAndLoginBcrypt(self):
        """
        Test user registration and logging in.
        """
        cherrypy.config['auth']['hash_alg'] = 'bcrypt'
        cherrypy.config['auth']['bcrypt_rounds'] = 4 # Set this to minimum so test runs faster.

        params = {
            'email' : 'bad_email',
            'login' : 'illegal@login',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'bad'
        }
        # First test all of the required parameters.
        self.ensureRequiredParams(path='/user', method='POST', required=params.keys())

        # Now test parameter validation
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'password')
        self.assertEqual(cherrypy.config['users']['password_description'], resp.json['message'])

        params['password'] = 'goodpassword'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')

        params['login'] = ' ' # something that violates the regex but doesn't contain @
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')
        self.assertEqual(cherrypy.config['users']['login_description'], resp.json['message'])

        params['login'] = 'goodlogin'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'email')

        # Now successfully create the user
        params['email'] = 'good@email.com'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)

        self.assertEqual(resp.json['hashAlg'], 'bcrypt')

        # Now that our user is created, try to login
        params = {
            'login' : 'incorrect@email.com',
            'password' : 'badpassword'
        }
        self.ensureRequiredParams(path='/user/login', method='POST', required=params.keys())

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
        self.assertHasKeys(resp.json['authToken'], ['token', 'expires', 'userId'])

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
            'email' : 'good@email.com',
            'login' : 'goodlogin',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'goodpassword'
        }

        # Register a user with sha512 storage backend
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)
        self.assertEqual(resp.json['hashAlg'], 'sha512')

        # Login unsuccessfully
        resp = self.request(path='/user/login', method='POST', params={
              'login' : params['login'],
              'password' : params['password'] + '.'
              })
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully
        resp = self.request(path='/user/login', method='POST', params={
              'login' : params['login'],
              'password' : params['password']
              })
        self.assertStatusOk(resp)
        self.assertEqual('Login succeeded.', resp.json['message'])

        # Make sure we got a nice cookie
        self._verifyAuthCookie(resp)

    def testGetUser(self):
        """
        Tests for the GET user endpoint.
        """
        params = {
            'email' : 'good@email.com',
            'login' : 'goodlogin',
            'firstName' : 'First',
            'lastName' : 'Last',
            'password' : 'goodpassword'
            }
        user = self.userModel.createUser(**params)
        resp = self.request(path='/user/%s' % user['_id'])
        self._verifyUserDocument(resp.json)

