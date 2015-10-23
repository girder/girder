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
import re
import six

from girder.constants import SettingKey
from server.constants import PluginSettings
from server.providers import _deriveLogin
from six.moves import urllib
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

        for input, expected in six.viewitems(expect):
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
        urlParts = urllib.parse.urlparse(resp.json['Google'])
        queryParams = urllib.parse.parse_qs(urlParts.query)
        self.assertEqual(urlParts.scheme, 'https')
        self.assertEqual(urlParts.netloc, 'accounts.google.com')
        self.assertEqual(queryParams['response_type'], ['code'])
        self.assertEqual(queryParams['access_type'], ['online'])
        self.assertEqual(queryParams['scope'], ['profile email'])
        self.assertEqual(queryParams['redirect_uri'],
                         ['http://127.0.0.1/api/v1/oauth/google/callback'])
        self.assertEqual(queryParams['state'][0], 'http://localhost/#foo/bar')
        self.assertEqual(len(resp.cookie), 1)

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
        self.assertEqual(len(resp.cookie), 1)
        self.assertEqual(resp.cookie['oauthLogin'].value, '')

        # Test logging in with an existing user

        # Get a fresh token since last one was destroyed
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        cookie = resp.cookie

        email = 'admin@mail.com'

        @httmock.all_requests
        def googleMock(url, request):
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

        with httmock.HTTMock(googleMock):
            resp = self.request('/oauth/google/callback', isJson=False, params={
                'code': '12345',
                'state': 'http://localhost/#foo/bar'
            }, cookie=self._createCsrfCookie(cookie))

        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertEqual(len(resp.cookie), 2)
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
        with httmock.HTTMock(googleMock):
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

        with httmock.HTTMock(googleMock):
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

        # Logging in as Oauth-only user should give reasonable error
        resp = self.request('/user/authentication',
                            basicAuth='anotheruser:mypassword')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You don\'t have a password. '
                         'Please log in with Google or use the password reset '
                         'link.')

        # Test receiving a bad status from google, make sure we show some
        # helpful output.
        errorContent = {'message': 'error'}
        @httmock.all_requests
        def errorResponse(url, request):
            return httmock.response(
                status_code=403, content=json.dumps(errorContent))

        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatusOk(resp)
        cookie = resp.cookie

        with httmock.HTTMock(errorResponse):
            resp = self.request('/oauth/google/callback', params={
                'code': '12345',
                'state': 'http://localhost/#foo/bar'
            }, exception=True, cookie=self._createCsrfCookie(cookie))
            self.assertStatus(resp, 502)
            self.assertEqual(
                resp.json['message'],
                'Got 403 from https://accounts.google.com/o/oauth2/token, '
                'response="{"message": "error"}".')

        # Reset password as oauth user should work
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={'email': email})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'], 'Sent temporary access email.')
        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail()

        # Pull out the auto-generated token from the email
        search = re.search('<a href="(.*)">', msg)
        link = search.group(1)
        linkParts = link.split('/')
        userId = linkParts[-3]
        tokenId = linkParts[-1]
        tempToken = self.model('token').load(
            tokenId, force=True, objectId=False)

        path = '/user/password/temporary/' + str(newUser['_id'])
        resp = self.request(path=path, method='GET', params={'token': tokenId})
        self.assertStatusOk(resp)
        user = resp.json['user']

        # We should now be able to change the password
        resp = self.request(path='/user/password', method='PUT', params={
            'old': tokenId,
            'new': 'mypasswd'
        }, user=user)
        self.assertStatusOk(resp)

        # The temp token should get deleted on password change
        token = self.model('token').load(tempToken, force=True, objectId=False)
        self.assertEqual(token, None)

    def _createCsrfCookie(self, cookie):
        info = json.loads(cookie['oauthLogin'].value)
        return 'oauthLogin="%s"' % json.dumps({
            'redirect': info['redirect'],
            'token': info['token'],
        }).replace('"', r'\"')
