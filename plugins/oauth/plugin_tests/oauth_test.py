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

import httmock
import json
import urlparse

from girder.constants import SettingKey
from server.constants import PluginSettings
from server.providers import _deriveLogin
from tests import base


def setUpModule():
    base.enabledPlugins.append('oauth')
    base.startServer()


def tearDownModule():
    base.stopServer()


class OauthTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.admin = self.model('user').createUser(
            email='admin@mail.com',
            login='admin',
            firstName='first',
            lastName='last',
            password='password',
            admin=True
        )

    def testDeriveLogin(self):
        """
        Unit test of _deriveLogin helper method.
        """
        expect = {
            'admin@google.com': None,  # duplicate of existing admin user
            '234@mail.com': None,  # violates regex even after coercion
            'hello.world.foo@mail.com': 'helloworldfoo',
            'first-last@mail.com': 'first-last'
        }

        for input, expected in expect.items():
            output = _deriveLogin(input, self.model('user'))
            self.assertEqual(output, expected)

    def testGoogleOauth(self):
        # Close registration to start off.
        self.model('setting').set(SettingKey.REGISTRATION_POLICY, 'closed')

        # We should get a 500 if no client ID is set
        resp = self.request('/oauth/provider', exception=True, params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatus(resp, 500)
        self.assertTrue(
            resp.json['message'].find(
                'No Google client ID setting is present.'
            ) >= 0
        )

        params = {
            'list': json.dumps([{
                'key': PluginSettings.GOOGLE_CLIENT_ID,
                'value': 'foo'
            }, {
                'key': PluginSettings.GOOGLE_CLIENT_SECRET,
                'value': 'bar'
            }])
        }

        resp = self.request(
            '/system/setting', user=self.admin, method='PUT', params=params)
        self.assertStatusOk(resp)

        params = {
            'list': json.dumps([
                PluginSettings.GOOGLE_CLIENT_ID,
                PluginSettings.GOOGLE_CLIENT_SECRET
            ])
        }
        resp = self.request(
            '/system/setting', user=self.admin, method='GET', params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            PluginSettings.GOOGLE_CLIENT_ID: 'foo',
            PluginSettings.GOOGLE_CLIENT_SECRET: 'bar'
        })

        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        self.assertTrue('Google' in resp.json)
        urlParts = urlparse.urlparse(resp.json['Google'])
        queryParams = urlparse.parse_qs(urlParts.query)
        self.assertEqual(urlParts.scheme, 'https')
        self.assertEqual(urlParts.netloc, 'accounts.google.com')
        self.assertEqual(queryParams['response_type'], ['code'])
        self.assertEqual(queryParams['access_type'], ['online'])
        self.assertEqual(queryParams['scope'], ['profile email'])
        self.assertEqual(queryParams['redirect_uri'],
                         ['http://127.0.0.1/api/v1/oauth/google/callback'])
        self.assertEqual(queryParams['state'][0], 'http://localhost/#foo/bar')
        self.assertEqual(len(resp.cookie.values()), 1)

        cookie = resp.cookie

        # Test the error condition for google callback
        resp = self.request('/oauth/google/callback', params={
            'code': None,
            'error': 'access_denied',
            'state': queryParams['state'][0]
        }, exception=True)
        self.assertStatus(resp, 500)
        self.assertTrue(
            resp.json['message'].find(
                'No CSRF cookie (state="http://localhost/#foo/bar").'
            ) >= 0
        )

        resp = self.request('/oauth/google/callback', isJson=False, params={
            'code': None,
            'error': 'access_denied',
            'state': queryParams['state'][0]
        }, cookie=self._createCsrfCookie(cookie))
        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'], 'http://localhost/#foo/bar')
        self.assertEqual(len(resp.cookie.values()), 1)
        self.assertEqual(resp.cookie['oauthLogin'].value, '')

        # Test logging in with an existing user

        # Get a fresh token since last one was destroyed
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        cookie = resp.cookie

        email = 'admin@mail.com'

        @httmock.all_requests
        def google_mock(url, request):
            if url.netloc == 'accounts.google.com':
                return json.dumps({
                    'token_type': 'Bearer',
                    'access_token': 'abcd'
                })
            elif url.netloc == 'www.googleapis.com':
                return json.dumps({
                    'name': {
                        'givenName': 'John',
                        'familyName': 'Doe'
                    },
                    'emails': [{
                        'type': 'account',
                        'value': email
                    }],
                    'id': 9876
                })
            else:
                raise Exception('Unexpected url {}'.format(url))

        with httmock.HTTMock(google_mock):
            resp = self.request('/oauth/google/callback', isJson=False, params={
                'code': '12345',
                'state': 'http://localhost/#foo/bar'
            }, cookie=self._createCsrfCookie(cookie))

        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertEqual(len(resp.cookie.values()), 2)
        self.assertTrue('oauthLogin' in resp.cookie)
        self.assertTrue('girderToken' in resp.cookie)
        self.assertEqual(resp.cookie['oauthLogin'].value, '')

        # Test login in with a new user

        # Get a fresh token
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        cookie = resp.cookie

        email = 'anotheruser@mail.com'
        with httmock.HTTMock(google_mock):
            resp = self.request('/oauth/google/callback', params={
                'code': '12345',
                'state': 'http://localhost/#foo/bar'
            }, cookie=self._createCsrfCookie(cookie))
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Registration on this instance is closed. Contact an '
                         'administrator to create an account for you.')

        # Open registration
        self.model('setting').set(SettingKey.REGISTRATION_POLICY, 'open')

        # Get a fresh token
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        cookie = resp.cookie

        with httmock.HTTMock(google_mock):
            resp = self.request('/oauth/google/callback', isJson=False, params={
                'code': '12345',
                'state': 'http://localhost/#foo/bar'
            }, cookie=self._createCsrfCookie(cookie))
        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertTrue('oauthLogin' in resp.cookie)
        self.assertTrue('girderToken' in resp.cookie)
        self.assertEqual(resp.cookie['oauthLogin'].value, '')

        token = self.model('token').load(resp.cookie['girderToken'].value,
                                         force=True, objectId=False)
        newUser = self.model('user').load(token['userId'], force=True)
        self.assertEqual(newUser['login'], 'anotheruser')
        self.assertEqual(newUser['email'], 'anotheruser@mail.com')
        self.assertEqual(newUser['oauth'], {
            'provider': 'Google',
            'id': 9876
        })
        self.assertEqual(newUser['firstName'], 'John')
        self.assertEqual(newUser['lastName'], 'Doe')

    def _createCsrfCookie(self, cookie):
        info = json.loads(cookie['oauthLogin'].value)
        return 'oauthLogin="{}"'.format(json.dumps({
            'redirect': info['redirect'],
            'token': info['token'],
        }).replace('"', "\\\""))
