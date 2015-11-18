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

from girder.constants import SettingKey
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
        Unit tests the _deriveLogin method of the provider classes.
        """
        from girder.plugins.oauth.providers import Google
        provider = Google(None)

        login = provider._deriveLogin('1234@mail.com', 'John', 'Doe')
        self.assertEqual(login, 'johndoe')

        login = provider._deriveLogin('hello.world.foo@mail.com', 'A', 'B')
        self.assertEqual(login, 'helloworldfoo')

        login = provider._deriveLogin('hello.world@mail.com', 'A', 'B', 'user2')
        self.assertEqual(login, 'user2')

        login = provider._deriveLogin('admin@admin.com', 'A', 'B', 'admin')
        self.assertEqual(login, 'admin1')

    def _getCsrfToken(self, resp, providerName):
        for provider in resp.json:
            if provider['id'] == providerName:
                providerUrl = provider['url']
                urlParts = urllib.parse.urlparse(providerUrl)
                queryParams = urllib.parse.parse_qs(urlParts.query)
                csrfToken = queryParams['state'][0]
                return csrfToken
        else:
            self.fail()

    def testGoogleOauth(self):
        from girder.plugins.oauth.constants import PluginSettings

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

        # Make sure that if no list param is passed, we receive the old format
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'
        })
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, dict)
        self.assertEqual(list(resp.json.keys()), ['Google'])
        self.assertRegexpMatches(
            resp.json['Google'],
            r'^https://accounts\.google\.com/o/oauth2/auth')

        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, list)
        for provider in resp.json:
            self.assertHasKeys(provider, ('id', 'name', 'url'))
            if provider['id'] == 'google':
                self.assertEqual(provider['name'], 'Google')
                providerUrl = provider['url']
                break
        else:
            self.fail()
        urlParts = urllib.parse.urlparse(providerUrl)
        queryParams = urllib.parse.parse_qs(urlParts.query)
        self.assertEqual(urlParts.scheme, 'https')
        self.assertEqual(urlParts.netloc, 'accounts.google.com')
        self.assertEqual(queryParams['response_type'], ['code'])
        self.assertEqual(queryParams['access_type'], ['online'])
        self.assertEqual(queryParams['client_id'], ['foo'])
        self.assertRegexpMatches(queryParams['redirect_uri'][0],
            r'http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/google/callback')
        self.assertEqual(queryParams['state'][0].partition('.')[2],
                         'http://localhost/#foo/bar')
        self.assertEqual(queryParams['scope'], ['profile email'])

        # Test the error condition for google callback
        resp = self.request('/oauth/google/callback', params={
            'code': None,
            'error': 'access_denied',
        }, exception=True)
        self.assertStatus(resp, 502)
        self.assertEqual(
            resp.json['message'],
            "Provider returned error: 'access_denied'."
        )

        # Test logging in with an existing user

        email = 'admin@mail.com'

        @httmock.all_requests
        def googleMock(url, request):
            if url.netloc == 'accounts.google.com':
                params = urllib.parse.parse_qs(request.body)
                if params.get('code') != ['12345']:
                    return {
                        'status_code': 401,
                        'content': json.dumps({
                            'error': 'Bad code'
                        })
                    }
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
            # Try a request where the CSRF token is incorrect
            resp = self.request('/oauth/google/callback', params={
                'code': '12345',
                'state': 'blah'
            })
            self.assertStatus(resp, 403)
            self.assertTrue(resp.json['message'].startswith(
                'Invalid CSRF token'))

        # Test login in with a new user

        # Get a fresh token
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        csrfToken = self._getCsrfToken(resp, 'google')

        email = 'anotheruser@mail.com'
        with httmock.HTTMock(googleMock):
            resp = self.request('/oauth/google/callback', params={
                'code': '12345',
                'state': csrfToken
            })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Registration on this instance is closed. Contact an '
                         'administrator to create an account for you.')

        # Open registration
        self.model('setting').set(SettingKey.REGISTRATION_POLICY, 'open')

        # Get a fresh token
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        csrfToken = self._getCsrfToken(resp, 'google')

        with httmock.HTTMock(googleMock):
            resp = self.request('/oauth/google/callback', isJson=False, params={
                'code': '12345',
                'state': csrfToken
            })
        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertTrue('girderToken' in resp.cookie)

        token = self.model('token').load(resp.cookie['girderToken'].value,
                                         force=True, objectId=False)
        newUser = self.model('user').load(token['userId'], force=True)
        self.assertEqual(newUser['login'], 'anotheruser')
        self.assertEqual(newUser['email'], 'anotheruser@mail.com')
        self.assertIn({'provider': 'google', 'id': 9876}, newUser['oauth'])
        self.assertEqual(newUser['firstName'], 'John')
        self.assertEqual(newUser['lastName'], 'Doe')

        # Logging in as OAuth-only user should give reasonable error
        resp = self.request('/user/authentication',
                            basicAuth='anotheruser:mypassword')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You don\'t have a password. '
                         'Please log in with Google, or use the password reset '
                         'link.')

        # Test receiving a bad status from Google, make sure we show some
        # helpful output.
        errorContent = {'message': 'error'}
        @httmock.all_requests
        def errorResponse(url, request):
            return httmock.response(
                status_code=403, content=json.dumps(errorContent))

        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        csrfToken = self._getCsrfToken(resp, 'google')

        with httmock.HTTMock(errorResponse):
            resp = self.request('/oauth/google/callback', params={
                'code': '12345',
                'state': csrfToken
            }, exception=True)
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

    def testGitHubOauth(self):
        from girder.plugins.oauth.constants import PluginSettings

        self.model('setting').set(PluginSettings.PROVIDERS_ENABLED, ['github'])

        resp = self.request('/oauth/provider', exception=True, params={
            'redirect': 'http://localhost/#foo/bar'})
        self.assertStatus(resp, 500)
        self.assertTrue(
            resp.json['message'].find(
                'No GitHub client ID setting is present.'
            ) >= 0
        )

        self.model('setting').set(PluginSettings.GITHUB_CLIENT_ID, 'abc')
        self.model('setting').set(PluginSettings.GITHUB_CLIENT_SECRET, '123')

        resp = self.request('/oauth/provider', exception=True, params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })

        self.assertStatusOk(resp)
        for provider in resp.json:
            self.assertHasKeys(provider, ('id', 'name', 'url'))
            if provider['id'] == 'github':
                self.assertEqual(provider['name'], 'GitHub')
                providerUrl = provider['url']
                break
        else:
            self.fail()
        self.assertEqual(len(resp.json), 1)  # Only one provider enabled
        urlParts = urllib.parse.urlparse(providerUrl)
        queryParams = urllib.parse.parse_qs(urlParts.query)
        self.assertEqual(urlParts.scheme, 'https')
        self.assertEqual(urlParts.netloc, 'github.com')
        self.assertEqual(urlParts.path, '/login/oauth/authorize')
        self.assertEqual(queryParams['client_id'], ['abc'])
        self.assertRegexpMatches(queryParams['redirect_uri'][0],
            r'http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/github/callback')
        self.assertEqual(queryParams['state'][0].partition('.')[2],
                         'http://localhost/#foo/bar')
        self.assertEqual(queryParams['scope'], ['user:email'])
        # Save this valid token for later
        csrfToken = self._getCsrfToken(resp, 'github')

        # Test the error condition for callback
        resp = self.request('/oauth/github/callback', params={
            'code': None,
            'error': 'access_denied',
        }, exception=True)
        self.assertStatus(resp, 502)
        self.assertEqual(
            resp.json['message'],
            "Provider returned error: 'access_denied'."
        )

        # Test login with a new user

        @httmock.all_requests
        def githubMock(url, request):
            if (url.netloc == 'github.com' and
                    url.path == '/login/oauth/access_token'):
                return json.dumps({
                    'token_type': 'bearer',
                    'access_token': 'abcd',
                    'scope': ['user:email']
                })
            elif (url.netloc == 'api.github.com' and
                    url.path == '/user'):
                return json.dumps({
                    'name': 'John Doe',
                    'login': 'johndoe',
                    'id': 1234
                })
            elif (url.netloc == 'api.github.com' and
                    url.path == '/user/emails'):
                return json.dumps([{
                    'primary': False,
                    'email': 'secondary@email.com',
                    'verified': True
                }, {
                    'primary': True,
                    'email': 'primary@email.com',
                    'verified': True
                }])
            else:
                raise Exception('Unexpected url %s' % str(url))

        with httmock.HTTMock(githubMock):
            resp = self.request('/oauth/github/callback', isJson=False, params={
                'code': '12345',
                'state': csrfToken
            })

        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertTrue('girderToken' in resp.cookie)

        resp = self.request('/user/me', token=resp.cookie['girderToken'].value)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['email'], 'primary@email.com')
        self.assertEqual(resp.json['login'], 'johndoe')
        self.assertEqual(resp.json['firstName'], 'John')
        self.assertEqual(resp.json['lastName'], 'Doe')
        newUserId = resp.json['_id']

        # Test login as an existing user
        email = 'admin@mail.com'

        # Get a fresh token
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        csrfToken = self._getCsrfToken(resp, 'github')

        with httmock.HTTMock(githubMock):
            resp = self.request('/oauth/github/callback', isJson=False, params={
                'code': '12345',
                'state': csrfToken
            })

        self.assertStatus(resp, 303)
        self.assertEqual(resp.headers['Location'],
                         'http://localhost/#foo/bar')
        self.assertTrue('girderToken' in resp.cookie)

        token = self.model('token').load(resp.cookie['girderToken'].value,
                                         force=True, objectId=False)
        newUser = self.model('user').load(token['userId'], force=True)
        self.assertEqual(str(newUser['_id']), newUserId)
        self.assertEqual(newUser['email'], 'primary@email.com')
        self.assertIn({'provider': 'github', 'id': 1234}, newUser['oauth'])
