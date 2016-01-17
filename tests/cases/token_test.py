#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013, 2014 Kitware Inc.
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

import random

from .. import base
from girder.constants import SettingKey, TokenScope
from girder.models.token import genToken


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class TokensTestCase(base.TestCase):

    def testCryptographicSecurity(self):
        # Make sure we are not using the normal random to generate tokens
        random.seed(1)
        token1 = genToken()
        random.seed(1)
        token2 = genToken()

        self.assertNotEqual(token1, token2)

    def atestGetAndDeleteSessiona(self):
        resp = self.request(path='/token/session', method='GET')
        self.assertStatusOk(resp)
        token = resp.json['token']
        # If we ask for another token, we should get a differnt one
        resp = self.request(path='/token/session', method='GET')
        self.assertStatusOk(resp)
        token2 = resp.json['token']
        self.assertNotEqual(token, token2)
        # If we ask for another token, passing in the first one, we should get
        # the first one back
        resp = self.request(path='/token/session', method='GET', token=token)
        self.assertStatusOk(resp)
        token2 = resp.json['token']
        self.assertEqual(token, token2)
        # If we ask about the current token without passing one, we should get
        # null
        resp = self.request(path='/token/current', method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)
        # With a token, we get the token document in the response
        resp = self.request(path='/token/current', method='GET', token=token)
        self.assertStatusOk(resp)
        self.assertEqual(token, resp.json['_id'])
        # Trying to delete a token without specifying one results in an error
        resp = self.request(path='/token/session', method='DELETE')
        self.assertStatus(resp, 401)
        # With the token should succeed
        resp = self.request(path='/token/session', method='DELETE', token=token)
        self.assertStatusOk(resp)
        # Now the token is gone, so it should fail
        resp = self.request(path='/token/session', method='DELETE', token=token)
        self.assertStatus(resp, 401)

    def testTokenScopes(self):
        admin = self.model('user').createUser(
            email='admin@admin.com', firstName='admin', lastName='admin',
            login='admin', password='passwd')
        nonadmin = self.model('user').createUser(
            email='normal@normal.com', firstName='normal', lastName='normal',
            login='normal', password='passwd')
        adminSettingToken = self.model('token').createToken(
            user=admin, scope=TokenScope.READ_SETTINGS)
        adminEmailToken = self.model('token').createToken(
            user=admin, scope=TokenScope.USER_EMAIL_READ)
        nonadminToken = self.model('token').createToken(
            user=nonadmin, scope=TokenScope.READ_SETTINGS)

        # Reading settings as admin should work
        params = {'key': SettingKey.SMTP_PORT}
        path = '/system/setting'
        resp = self.request(path=path, params=params, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 25)

        # Reading setting as non-admin should fail
        resp = self.request(path=path, params=params, user=nonadmin)
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
