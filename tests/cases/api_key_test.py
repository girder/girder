#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import datetime
import json

from .. import base
from girder.constants import SettingKey, TokenScope


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ApiKeyTestCase(base.TestCase):
    def setUp(self):
        super(ApiKeyTestCase, self).setUp()

        self.admin = self.model('user').createUser(
            email='admin@email.com', login='admin', firstName='Admin',
            lastName='Admin', password='password', admin=True)

        self.user = self.model('user').createUser(
            email='user@email.com', login='goodlogin', firstName='First',
            lastName='Last', password='password', admin=False)

        self.defaultDuration = self.model('setting').get(
            SettingKey.COOKIE_LIFETIME)

    def testListScopes(self):
        resp = self.request('/token/scopes')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, TokenScope.listScopes())

        self.assertIn('custom', resp.json)
        self.assertIsInstance(resp.json['custom'], list)
        self.assertIn('adminCustom', resp.json)
        self.assertIsInstance(resp.json['adminCustom'], list)

        for scope in resp.json['custom'] + resp.json['adminCustom']:
            self.assertIn('id', scope)
            self.assertIn('name', scope)
            self.assertIn('description', scope)

    def testListKeys(self):
        # Normal users shouldn't be able to request other users' keys
        resp = self.request('/api_key', params={'userId': self.admin['_id']},
                            user=self.user)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Administrator access required.')

        # Users should be able to request their own keys
        resp = self.request('/api_key', params={'userId': self.user['_id']},
                            user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Passing no user ID should work
        resp = self.request('/api_key', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        # Admins should be able to see other users' keys
        resp = self.request('/api_key', params={'userId': self.user['_id']},
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

    def testKeyPolicies(self):
        # Create a new API key with full access
        resp = self.request('/api_key', method='POST', params={
            'name': 'test key'
        }, user=self.user)
        self.assertStatusOk(resp)
        apiKey = self.model('api_key').load(resp.json['_id'], force=True)
        self.assertEqual(apiKey['scope'], None)
        self.assertEqual(apiKey['name'], 'test key')
        self.assertEqual(apiKey['lastUse'], None)
        self.assertEqual(apiKey['tokenDuration'], None)
        self.assertEqual(apiKey['active'], True)

        # Create a token using the key
        resp = self.request('/api_key/token', method='POST', params={
            'key': apiKey['key'],
            'duration': self.defaultDuration + 1000
        })
        self.assertStatusOk(resp)
        token = self.model('token').load(
            resp.json['authToken']['token'], force=True, objectId=False)
        # Make sure token has full user auth access
        self.assertEqual(token['userId'], self.user['_id'])
        self.assertEqual(token['scope'], [TokenScope.USER_AUTH])
        # Make sure the token references the API key used to create it
        self.assertEqual(token['apiKeyId'], apiKey['_id'])

        # Make sure the token duration is not longer than the default
        duration = token['expires'] - token['created']
        self.assertEqual(duration,
                         datetime.timedelta(days=self.defaultDuration))

        # We should be able to request a duration shorter than default
        resp = self.request('/api_key/token', method='POST', params={
            'key': apiKey['key'],
            'duration': self.defaultDuration - 1
        })
        self.assertStatusOk(resp)
        token = self.model('token').load(
            resp.json['authToken']['token'], force=True, objectId=False)
        duration = token['expires'] - token['created']
        self.assertEqual(duration,
                         datetime.timedelta(days=self.defaultDuration - 1))

        # We should have two tokens for this key
        q = {
            'userId': self.user['_id'],
            'apiKeyId': apiKey['_id']
        }
        count = self.model('token').find(q).count()
        self.assertEqual(count, 2)

        # Deactivate the key and change the token duration and scope
        newScopes = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
        resp = self.request('/api_key/%s' % apiKey['_id'], params={
            'active': False,
            'tokenDuration': 10,
            'scope': json.dumps(newScopes)
        }, method='PUT', user=self.user)
        self.assertStatusOk(resp)
        # Make sure key itself didn't change
        self.assertEqual(resp.json['key'], apiKey['key'])
        apiKey = self.model('api_key').load(resp.json['_id'], force=True)
        self.assertEqual(apiKey['active'], False)
        self.assertEqual(apiKey['tokenDuration'], 10)
        self.assertEqual(set(apiKey['scope']), set(newScopes))
        # Should now have a last used timestamp
        self.assertIsInstance(apiKey['lastUse'], datetime.datetime)

        # This should have deleted all corresponding tokens
        q = {
            'userId': self.user['_id'],
            'apiKeyId': apiKey['_id']
        }
        count = self.model('token').find(q).count()
        self.assertEqual(count, 0)

        # We should not be able to create tokens for this key anymore
        resp = self.request('/api_key/token', method='POST', params={
            'key': apiKey['key']
        })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid API key.')

        # Reactivate key
        resp = self.request('/api_key/%s' % apiKey['_id'], params={
            'active': True
        }, method='PUT', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['key'], apiKey['key'])
        apiKey = self.model('api_key').load(resp.json['_id'], force=True)

        # Should now be able to make tokens with 10 day duration
        resp = self.request('/api_key/token', method='POST', params={
            'key': apiKey['key']
        })
        self.assertStatusOk(resp)
        token = self.model('token').load(
            resp.json['authToken']['token'], force=True, objectId=False)
        duration = token['expires'] - token['created']
        self.assertEqual(duration, datetime.timedelta(days=10))
        self.assertEqual(set(token['scope']), set(newScopes))

        # Deleting the API key should delete the tokens made with it
        count = self.model('token').find(q).count()
        self.assertEqual(count, 1)
        resp = self.request('/api_key/%s' % apiKey['_id'], method='DELETE',
                            user=self.user)
        self.assertStatusOk(resp)
        count = self.model('token').find(q).count()
        self.assertEqual(count, 0)
