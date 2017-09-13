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
from girder.constants import TokenScope
from girder.models.token import genToken
from girder.models.model_base import AccessException


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

    def testGetAndDeleteSession(self):
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

    def testHasScope(self):
        scope = TokenScope.DATA_READ
        tokenModel = self.model('token')
        token = tokenModel.createToken(scope=scope)

        # If token is None should return False
        self.assertFalse(tokenModel.hasScope(None, scope))

        # If scope is None should return True
        self.assertTrue(tokenModel.hasScope(token, None))

    def testRequireScope(self):
        scope = TokenScope.DATA_OWN
        anotherScope = TokenScope.SETTINGS_READ
        tokenModel = self.model('token')
        token = tokenModel.createToken(scope=scope)

        # If specified scope does not exist raise an error
        with self.assertRaises(AccessException):
            tokenModel.requireScope(token, anotherScope)
