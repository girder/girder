# -*- coding: utf-8 -*-
import datetime
import json
import re
import urllib.parse

import httmock
import jwt
import requests
import six

from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User
from girder.settings import SettingKey
import girder.events
from tests import base

from girder_oauth.providers.base import ProviderBase
from girder_oauth.providers.google import Google
from girder_oauth.settings import PluginSettings


def setUpModule():
    base.enabledPlugins.append('oauth')
    base.startServer()


def tearDownModule():
    base.stopServer()


class OauthTest(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        self.adminUser = User().createUser(
            email='rocky@phila.pa.us',
            login='rocky',
            firstName='Robert',
            lastName='Balboa',
            password='adrian',
            admin=True
        )

        # Specifies which test account (typically 'new' or 'existing') a
        # redirect to a provider will simulate authentication for
        self.accountType = None

    def testDeriveLogin(self):
        """
        Unit tests the _deriveLogin method of the provider classes.
        """
        login = ProviderBase._deriveLogin('1234@girder.test', 'John', 'Doe')
        self.assertEqual(login, 'johndoe')

        login = ProviderBase._deriveLogin('hello#world#foo@girder.test', 'A', 'B')
        self.assertEqual(login, 'helloworldfoo')

        login = ProviderBase._deriveLogin('hello.world@girder.test', 'A', 'B', 'user2')
        self.assertEqual(login, 'user2')

        # This should conflict with the saved admin user
        login = ProviderBase._deriveLogin('rocky@phila.pa.us', 'Robert', 'Balboa', 'rocky')
        self.assertEqual(login, 'rocky1')

    def _testSettings(self, providerInfo):
        Setting().set(SettingKey.REGISTRATION_POLICY, 'closed')
        self.accountType = 'new'

        # We should get an empty listing when no providers are set up
        params = {
            'key': PluginSettings.PROVIDERS_ENABLED,
            'value': []
        }
        resp = self.request('/system/setting', user=self.adminUser, method='PUT', params=params)
        self.assertStatusOk(resp)

        resp = self.request('/oauth/provider', exception=True, params={
            'redirect': 'http://localhost/#foo/bar',
            'list': True
        })
        self.assertStatusOk(resp)
        self.assertFalse(resp.json)

        # Turn on provider, but don't set other settings
        params = {
            'list': json.dumps([{
                'key': PluginSettings.PROVIDERS_ENABLED,
                'value': [providerInfo['id']]
            }])
        }
        resp = self.request('/system/setting', user=self.adminUser, method='PUT', params=params)
        self.assertStatusOk(resp)

        resp = self.request('/oauth/provider', exception=True, params={
            'redirect': 'http://localhost/#foo/bar'
        })
        self.assertStatus(resp, 500)

        # Set up provider normally
        params = {
            'list': json.dumps([
                {
                    'key': PluginSettings.PROVIDERS_ENABLED,
                    'value': [providerInfo['id']]
                }, {
                    'key': providerInfo['client_id']['key'],
                    'value': providerInfo['client_id']['value']
                }, {
                    'key': providerInfo['client_secret']['key'],
                    'value': providerInfo['client_secret']['value']
                }
            ])
        }
        resp = self.request('/system/setting', user=self.adminUser, method='PUT', params=params)
        self.assertStatusOk(resp)
        # No need to re-fetch and test all of these settings values; they will
        # be implicitly tested later

    def _testOauthEventHandling(self, providerInfo):
        self.accountType = 'existing'

        def _getCallbackParams(providerInfo, redirect):
            resp = self.request('/oauth/provider', params={
                'redirect': redirect,
                'list': True
            })
            providerResp = resp.json[0]
            resp = requests.get(providerResp['url'], allow_redirects=False)
            callbackLoc = urllib.parse.urlparse(resp.headers['location'])
            callbackLocQuery = urllib.parse.parse_qs(callbackLoc.query)
            callbackParams = {
                key: val[0] for key, val in six.viewitems(callbackLocQuery)
            }
            return callbackParams

        redirect = 'http://localhost/#foo/bar?token={girderToken}'

        class EventHandler(object):
            def __init__(self):
                self.state = ''

            def _oauth_before_stop(self, event):
                self.state = 'been in "before"'
                event.preventDefault()

            def _oauth_before(self, event):
                self.state = 'been in "before"'

            def _oauth_after(self, event):
                self.state = 'been in "after"'
                event.preventDefault()

        event_handler = EventHandler()

        params = _getCallbackParams(providerInfo, redirect)
        with girder.events.bound(
            'oauth.auth_callback.before',
            'oauth_before',
            event_handler._oauth_before_stop
        ), girder.events.bound(
            'oauth.auth_callback.after',
            'oauth_after',
            event_handler._oauth_after
        ):
            resp = self.request(
                '/oauth/%s/callback' % providerInfo['id'], params=params, isJson=False)
            self.assertStatus(resp, 303)
            self.assertTrue('girderToken' not in resp.cookie)
            self.assertEqual(event_handler.state, 'been in "before"')

        params = _getCallbackParams(providerInfo, redirect)
        with girder.events.bound(
            'oauth.auth_callback.before',
            'oauth_before',
            event_handler._oauth_before
        ), girder.events.bound(
            'oauth.auth_callback.after',
            'oauth_after',
            event_handler._oauth_after
        ):
            resp = self.request(
                '/oauth/%s/callback' % providerInfo['id'], params=params, isJson=False)
            self.assertStatus(resp, 303)
            self.assertTrue('girderToken' not in resp.cookie)
            self.assertEqual(event_handler.state, 'been in "after"')

    def _testOauthTokenAsParam(self, providerInfo):
        self.accountType = 'existing'

        def _getCallbackParams(providerInfo, redirect):
            resp = self.request('/oauth/provider', params={
                'redirect': redirect,
                'list': True
            })
            self.assertStatusOk(resp)
            providerResp = resp.json[0]
            resp = requests.get(providerResp['url'], allow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            callbackLoc = urllib.parse.urlparse(resp.headers['location'])
            self.assertEqual(
                callbackLoc.path, r'/api/v1/oauth/%s/callback' % providerInfo['id'])
            callbackLocQuery = urllib.parse.parse_qs(callbackLoc.query)
            self.assertNotHasKeys(callbackLocQuery, ('error',))
            callbackParams = {
                key: val[0] for key, val in six.viewitems(callbackLocQuery)
            }
            return callbackParams

        redirect = 'http://localhost/#foo/bar?token={girderToken}'
        params = _getCallbackParams(providerInfo, redirect)

        resp = self.request(
            '/oauth/%s/callback' % providerInfo['id'], params=params, isJson=False)
        self.assertStatus(resp, 303)
        self.assertTrue('girderToken' in resp.cookie)
        self.assertEqual(
            resp.headers['Location'],
            redirect.format(girderToken=resp.cookie['girderToken'].value))

        redirect = 'http://localhost/#foo/bar?token={foobar}'
        params = _getCallbackParams(providerInfo, redirect)

        resp = self.request(
            '/oauth/%s/callback' % providerInfo['id'], params=params, isJson=False)
        self.assertStatus(resp, 303)
        self.assertTrue('girderToken' in resp.cookie)
        self.assertEqual(resp.headers['Location'], redirect)

    def _testOauth(self, providerInfo):
        # Close registration to start off, and simulate a new user
        self._testSettings(providerInfo)

        # Make sure that if no list param is passed, we receive the old format
        resp = self.request('/oauth/provider', params={
            'redirect': 'http://localhost/#foo/bar'
        })
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, dict)
        self.assertEqual(len(resp.json), 1)
        self.assertIn(providerInfo['name'], resp.json)
        self.assertRegex(resp.json[providerInfo['name']], providerInfo['url_re'])

        # This will need to be called several times, to get fresh tokens
        def getProviderResp():
            resp = self.request('/oauth/provider', params={
                'redirect': 'http://localhost/#foo/bar',
                'list': True
            })
            self.assertStatusOk(resp)
            self.assertIsInstance(resp.json, list)
            self.assertEqual(len(resp.json), 1)
            providerResp = resp.json[0]
            self.assertSetEqual(set(six.viewkeys(providerResp)), {'id', 'name', 'url'})
            self.assertEqual(providerResp['id'], providerInfo['id'])
            self.assertEqual(providerResp['name'], providerInfo['name'])
            self.assertRegex(providerResp['url'], providerInfo['url_re'])
            redirectParams = urllib.parse.parse_qs(
                urllib.parse.urlparse(providerResp['url']).query)
            csrfTokenParts = redirectParams['state'][0].partition('.')
            token = Token().load(csrfTokenParts[0], force=True, objectId=False)
            self.assertLess(
                token['expires'],
                datetime.datetime.utcnow() + datetime.timedelta(days=0.30))
            self.assertEqual(csrfTokenParts[2], 'http://localhost/#foo/bar')
            return providerResp

        # Try the new format listing
        getProviderResp()

        # Try callback, for a nonexistent provider
        resp = self.request('/oauth/foobar/callback')
        self.assertStatus(resp, 400)

        # Try callback, without providing any params
        resp = self.request('/oauth/%s/callback' % providerInfo['id'])
        self.assertStatus(resp, 400)

        # Try callback, providing params as though the provider failed
        resp = self.request(
            '/oauth/%s/callback' % providerInfo['id'],
            params={
                'code': None,
                'error': 'some_custom_error',
            }, exception=True)
        self.assertStatus(resp, 502)
        self.assertEqual(resp.json['message'], "Provider returned error: 'some_custom_error'.")

        # This will need to be called several times, to use fresh tokens
        def getCallbackParams(providerResp):
            resp = requests.get(providerResp['url'], allow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            callbackLoc = urllib.parse.urlparse(resp.headers['location'])
            self.assertEqual(
                callbackLoc.path, r'/api/v1/oauth/%s/callback' % providerInfo['id'])
            callbackLocQuery = urllib.parse.parse_qs(callbackLoc.query)
            self.assertNotHasKeys(callbackLocQuery, ('error',))
            callbackParams = {
                key: val[0] for key, val in six.viewitems(callbackLocQuery)
            }
            return callbackParams

        # Call (simulated) external provider
        getCallbackParams(getProviderResp())

        # Try callback, with incorrect CSRF token
        params = getCallbackParams(getProviderResp())
        params['state'] = 'something_wrong'
        resp = self.request('/oauth/%s/callback' % providerInfo['id'], params=params)
        self.assertStatus(resp, 403)
        self.assertTrue(
            resp.json['message'].startswith('Invalid CSRF token'))

        # Try callback, with expired CSRF token
        params = getCallbackParams(getProviderResp())
        token = Token().load(params['state'].partition('.')[0], force=True, objectId=False)
        token['expires'] -= datetime.timedelta(days=1)
        Token().save(token)
        resp = self.request('/oauth/%s/callback' % providerInfo['id'], params=params)
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['message'].startswith('Expired CSRF token'))

        # Try callback, with a valid CSRF token but no redirect
        params = getCallbackParams(getProviderResp())
        params['state'] = params['state'].partition('.')[0]
        resp = self.request('/oauth/%s/callback' % providerInfo['id'], params=params)
        self.assertStatus(resp, 400)
        self.assertTrue(resp.json['message'].startswith('No redirect location'))

        # Try callback, with incorrect code
        params = getCallbackParams(getProviderResp())
        params['code'] = 'something_wrong'
        resp = self.request('/oauth/%s/callback' % providerInfo['id'], params=params)
        self.assertStatus(resp, 502)

        # Try callback, with real parameters from provider, but still for the
        # 'new' account
        params = getCallbackParams(getProviderResp())
        resp = self.request('/oauth/%s/callback' % providerInfo['id'], params=params)
        self.assertStatus(resp, 400)
        self.assertTrue(
            resp.json['message'].startswith('Registration on this instance is closed.'))

        # This will need to be called several times, and will do a normal login
        def doOauthLogin(accountType):
            self.accountType = accountType
            params = getCallbackParams(getProviderResp())
            resp = self.request(
                '/oauth/%s/callback' % providerInfo['id'], params=params, isJson=False)
            self.assertStatus(resp, 303)
            self.assertEqual(resp.headers['Location'], 'http://localhost/#foo/bar')
            self.assertTrue('girderToken' in resp.cookie)

            resp = self.request('/user/me', token=resp.cookie['girderToken'].value)
            user = resp.json
            self.assertStatusOk(resp)
            self.assertEqual(
                user['email'], providerInfo['accounts'][accountType]['user']['email'])
            self.assertEqual(
                user['login'], providerInfo['accounts'][accountType]['user']['login'])
            self.assertEqual(
                user['firstName'], providerInfo['accounts'][accountType]['user']['firstName'])
            self.assertEqual(
                user['lastName'], providerInfo['accounts'][accountType]['user']['lastName'])
            return user

        # Try callback for the 'existing' account, which should succeed
        existing = doOauthLogin('existing')

        # Hit validation exception on ignore registration policy setting
        with self.assertRaises(ValidationException):
            Setting().set(PluginSettings.IGNORE_REGISTRATION_POLICY, 'foo')

        # Try callback for the 'new' account, with registration policy ignored
        Setting().set(PluginSettings.IGNORE_REGISTRATION_POLICY, True)
        new = doOauthLogin('new')

        # Password login for 'new' OAuth-only user should fail gracefully
        newUser = providerInfo['accounts']['new']['user']
        resp = self.request('/user/authentication', basicAuth='%s:mypasswd' % newUser['login'])
        self.assertStatus(resp, 400)
        self.assertTrue(resp.json['message'].startswith("You don't have a password."))

        # Reset password for 'new' OAuth-only user should work
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        resp = self.request(
            '/user/password/temporary', method='PUT', params={
                'email': providerInfo['accounts']['new']['user']['email']})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'], 'Sent temporary access email.')
        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail(parse=True)
        # Pull out the auto-generated token from the email
        body = msg.get_payload(decode=True).decode('utf8')
        search = re.search('<a href="(.*)">', body)
        link = search.group(1)
        linkParts = link.split('/')
        userId = linkParts[-3]
        tokenId = linkParts[-1]
        tempToken = Token().load(tokenId, force=True, objectId=False)
        resp = self.request(
            '/user/password/temporary/' + userId, method='GET', params={'token': tokenId})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['user']['login'], newUser['login'])
        # We should now be able to change the password
        resp = self.request(
            '/user/password', method='PUT', user=resp.json['user'], params={
                'old': tokenId,
                'new': 'mypasswd'
            })
        self.assertStatusOk(resp)
        # The temp token should get deleted on password change
        token = Token().load(tempToken, force=True, objectId=False)
        self.assertEqual(token, None)

        # Password login for 'new' OAuth-only user should now succeed
        resp = self.request('/user/authentication', basicAuth='%s:mypasswd' % newUser['login'])
        self.assertStatusOk(resp)

        return existing, new

    @httmock.all_requests
    def mockOtherRequest(self, url, request):
        raise Exception('Unexpected url %s' % str(request.url))

    def testGoogleOauth(self):  # noqa
        providerInfo = {
            'id': 'google',
            'name': 'Google',
            'client_id': {
                'key': PluginSettings.GOOGLE_CLIENT_ID,
                'value': 'google_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.GOOGLE_CLIENT_SECRET,
                'value': 'google_test_client_secret'
            },
            'allowed_callback_re': r'^http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/google/callback$',
            'url_re': r'^https://accounts\.google\.com/o/oauth2/v2/auth',
            'accounts': {
                'existing': {
                    'auth_code': 'google_existing_auth_code',
                    'access_token': 'google_existing_test_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'google',
                            'id': '5326'
                        }
                    }
                },
                'new': {
                    'auth_code': 'google_new_auth_code',
                    'access_token': 'google_new_test_token',
                    'user': {
                        # this login is not provided by Google, but will be
                        # created internally by _deriveLogin
                        'login': 'creed',
                        'email': 'creed@la.ca.us',
                        'firstName': 'Apollo',
                        'lastName': 'Creed',
                        'oauth': {
                            'provider': 'google',
                            'id': 'the1best'
                        }
                    }
                }
            }
        }

        # Test inclusion of custom scope
        Google.addScopes(['custom_scope', 'foo'])

        @httmock.urlmatch(scheme='https', netloc=r'^accounts\.google\.com$',
                          path=r'^/o/oauth2/v2/auth$', method='GET')
        def mockGoogleRedirect(url, request):
            try:
                params = urllib.parse.parse_qs(url.query)
                self.assertEqual(params['response_type'], ['code'])
                self.assertEqual(params['access_type'], ['online'])
                self.assertEqual(params['scope'], ['openid profile email custom_scope foo'])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            returnQuery = urllib.parse.urlencode({
                'state': state,
                'code': providerInfo['accounts'][self.accountType]['auth_code']
            })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (params['redirect_uri'][0], returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc=r'^oauth2\.googleapis\.com$',
                          path=r'^/token$', method='POST')
        def mockGoogleToken(url, request):
            try:
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertEqual(params['grant_type'], ['authorization_code'])
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            return json.dumps({
                'token_type': 'Bearer',
                'access_token': account['access_token'],
                'expires_in': 3546,
                'id_token': jwt.encode({
                    'sub': account['user']['oauth']['id'],
                    'email': account['user']['email'],
                }, 'secret').decode()
            })

        @httmock.urlmatch(scheme='https', netloc=r'^accounts\.google\.com$',
                          path=r'^/.well-known/openid-configuration$', method='GET')
        def mockGoogleDiscovery(url, request):
            return json.dumps({
                'userinfo_endpoint': 'https://openidconnect.googleapis.com/v1/userinfo'
            })

        @httmock.urlmatch(scheme='https', netloc=r'^openidconnect\.googleapis\.com$',
                          path=r'^/v1/userinfo$', method='GET')
        def mockGoogleApi(url, request):
            for account in six.viewvalues(providerInfo['accounts']):
                if 'Bearer %s' % account['access_token'] == request.headers['Authorization']:
                    break
            else:
                self.fail()

            return json.dumps({
                'sub': account['user']['oauth']['id'],
                'given_name': account['user']['firstName'],
                'family_name': account['user']['lastName'],
                'email': account['user']['email']
            })

        with httmock.HTTMock(
            mockGoogleRedirect,
            mockGoogleToken,
            mockGoogleDiscovery,
            mockGoogleApi,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)

    def testGithubOauth(self):  # noqa
        providerInfo = {
            'id': 'github',
            'name': 'GitHub',
            'client_id': {
                'key': PluginSettings.GITHUB_CLIENT_ID,
                'value': 'github_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.GITHUB_CLIENT_SECRET,
                'value': 'github_test_client_secret'
            },
            'allowed_callback_re':
                r'^http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/github/callback$',
            'url_re': r'^https://github\.com/login/oauth/authorize',
            'accounts': {
                'existing': {
                    'auth_code': 'github_existing_auth_code',
                    'access_token': 'github_existing_test_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'github',
                            'id': '2399'
                        }
                    }
                },
                'new': {
                    'auth_code': 'github_new_auth_code',
                    'access_token': 'github_new_test_token',
                    'user': {
                        # login may be provided externally by GitHub; for
                        # simplicity here, do not use a username with whitespace
                        # or underscores
                        'login': 'drago',
                        'email': 'metaphor@labs.ussr.gov',
                        'firstName': 'Ivan',
                        'lastName': 'Drago',
                        'oauth': {
                            'provider': 'github',
                            'id': 1985
                        }
                    }
                }
            }
        }

        @httmock.urlmatch(scheme='https', netloc='^github.com$',
                          path='^/login/oauth/authorize$', method='GET')
        def mockGithubRedirect(url, request):
            redirectUri = None
            try:
                params = urllib.parse.parse_qs(url.query)
                # Check redirect_uri first, so other errors can still redirect
                redirectUri = params['redirect_uri'][0]
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertRegex(redirectUri, providerInfo['allowed_callback_re'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
                self.assertEqual(params['scope'], ['user:email'])
            except (KeyError, AssertionError) as e:
                returnQuery = urllib.parse.urlencode({
                    'error': repr(e),
                })
            else:
                returnQuery = urllib.parse.urlencode({
                    'state': state,
                    'code': providerInfo['accounts'][self.accountType]['auth_code']
                })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (redirectUri, returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc='^github.com$',
                          path='^/login/oauth/access_token$', method='POST')
        def mockGithubToken(url, request):
            try:
                self.assertEqual(request.headers['Accept'], 'application/json')
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
            except (KeyError, AssertionError) as e:
                returnBody = json.dumps({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnBody = json.dumps({
                    'token_type': 'bearer',
                    'access_token': account['access_token'],
                    'scope': 'user:email'
                })
            return {
                'status_code': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'content': returnBody
            }

        @httmock.urlmatch(scheme='https', netloc='^api.github.com$', path='^/user$', method='GET')
        def mockGithubApiUser(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'token %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'id': account['user']['oauth']['id'],
                'login': account['user']['login'],
                'name': '%s %s' % (account['user']['firstName'], account['user']['lastName'])
            })

        @httmock.urlmatch(scheme='https', netloc='^api.github.com$',
                          path='^/user/emails$', method='GET')
        def mockGithubApiEmail(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'token %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps([
                {
                    'primary': False,
                    'email': 'drago@siberia.ussr.gov',
                    'verified': True
                }, {
                    'primary': True,
                    'email': account['user']['email'],
                    'verified': True
                }
            ])

        with httmock.HTTMock(
            mockGithubRedirect,
            mockGithubToken,
            mockGithubApiUser,
            mockGithubApiEmail,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)

        @httmock.urlmatch(scheme='https', netloc='^api.github.com$', path='^/user$', method='GET')
        def mockGithubUserWithoutName(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'token %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'id': account['user']['oauth']['id'],
                'login': account['user']['login'],
                'name': None
            })

        self.setUp()  # Call to reset everything so we can call _testOauth again

        # If no name is provided, we expect to use the github login for both
        providerInfo['accounts']['existing']['user']['lastName'] = 'rocky'
        providerInfo['accounts']['existing']['user']['firstName'] = 'rocky'

        providerInfo['accounts']['new']['user']['lastName'] = 'drago'
        providerInfo['accounts']['new']['user']['firstName'] = 'drago'

        with httmock.HTTMock(
            mockGithubRedirect,
            mockGithubToken,
            mockGithubUserWithoutName,
            mockGithubApiEmail,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)

    def testGlobusOauth(self):  # noqa
        providerInfo = {
            'id': 'globus',
            'name': 'Globus',
            'client_id': {
                'key': PluginSettings.GLOBUS_CLIENT_ID,
                'value': 'globus_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.GLOBUS_CLIENT_SECRET,
                'value': 'globus_test_client_secret'
            },
            'scope': 'urn:globus:auth:scope:auth.globus.org:view_identities openid profile email',
            'allowed_callback_re':
                r'^http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/globus/callback$',
            'url_re': r'^https://auth.globus.org/v2/oauth2/authorize',
            'accounts': {
                'existing': {
                    'auth_code': 'globus_existing_auth_code',
                    'access_token': 'globus_existing_test_token',
                    'id_token': 'globus_exisiting_id_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'globus',
                            'id': '2399'
                        }
                    }
                },
                'new': {
                    'auth_code': 'globus_new_auth_code',
                    'access_token': 'globus_new_test_token',
                    'id_token': 'globus_new_id_token',
                    'user': {
                        'login': 'metaphor',
                        'email': 'metaphor@labs.ussr.gov',
                        'firstName': 'Ivan',
                        'lastName': 'Drago',
                        'oauth': {
                            'provider': 'globus',
                            'id': 1985
                        }
                    }
                }
            }
        }

        @httmock.urlmatch(scheme='https', netloc='^auth.globus.org$',
                          path='^/v2/oauth2/authorize$', method='GET')
        def mockGlobusRedirect(url, request):
            try:
                params = urllib.parse.parse_qs(url.query)
                self.assertEqual(params['response_type'], ['code'])
                self.assertEqual(params['access_type'], ['online'])
                self.assertEqual(params['scope'], [providerInfo['scope']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            returnQuery = urllib.parse.urlencode({
                'state': state,
                'code': providerInfo['accounts'][self.accountType]['auth_code']
            })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (params['redirect_uri'][0], returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc='^auth.globus.org$',
                          path='^/v2/oauth2/userinfo$', method='GET')
        def mockGlobusUserInfo(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'Bearer %s' % account['access_token'] == \
                            request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            user = account['user']
            return json.dumps({
                'email': user['email'],
                'preferred_username': user['email'],
                'sub': user['oauth']['id'],
                'name': '{firstName} {lastName}'.format(**user),
            })

        @httmock.urlmatch(scheme='https', netloc='^auth.globus.org$',
                          path='^/v2/oauth2/token$', method='POST')
        def mockGlobusToken(url, request):
            try:
                self.assertEqual(request.headers['Accept'], 'application/json')
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
            except (KeyError, AssertionError) as e:
                returnBody = json.dumps({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnBody = json.dumps({
                    'access_token': account['access_token'],
                    'resource_server': 'auth.globus.org',
                    'expires_in': 3600,
                    'token_type': 'bearer',
                    'scope': 'urn:globus:auth:scope:auth.globus.org:monitor_ongoing',
                    'refresh_token': 'blah',
                    'id_token': account['id_token'],
                    'state': 'provided_by_client_to_prevent_replay_attacks',
                    'other_tokens': [],
                })
            return {
                'status_code': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'content': returnBody
            }

        with httmock.HTTMock(
            mockGlobusRedirect,
            mockGlobusUserInfo,
            mockGlobusToken,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)
            self._testOauthTokenAsParam(providerInfo)
            self._testOauthEventHandling(providerInfo)

    def testLinkedinOauth(self):  # noqa
        providerInfo = {
            'id': 'linkedin',
            'name': 'LinkedIn',
            'client_id': {
                'key': PluginSettings.LINKEDIN_CLIENT_ID,
                'value': 'linkedin_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.LINKEDIN_CLIENT_SECRET,
                'value': 'linkedin_test_client_secret'
            },
            'allowed_callback_re':
                r'^http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/linkedin/callback$',
            'url_re': r'^https://www\.linkedin\.com/uas/oauth2/authorization',
            'accounts': {
                'existing': {
                    'auth_code': 'linkedin_existing_auth_code',
                    'access_token': 'linkedin_existing_test_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'linkedin',
                            'id': '42kD-5H'
                        }
                    }
                },
                'new': {
                    'auth_code': 'linkedin_new_auth_code',
                    'access_token': 'linkedin_new_test_token',
                    'user': {
                        # this login is not provided by LinkedIn, but will be
                        # created internally by _deriveLogin
                        'login': 'clubber',
                        'email': 'clubber@streets.chi.il.us',
                        'firstName': 'James',
                        'lastName': 'Lang',
                        'oauth': {
                            'provider': 'linkedin',
                            'id': '634pity-fool4'
                        }
                    }
                }
            }
        }

        @httmock.urlmatch(scheme='https', netloc='^www.linkedin.com$',
                          path='^/uas/oauth2/authorization$', method='GET')
        def mockLinkedinRedirect(url, request):
            try:
                params = urllib.parse.parse_qs(url.query)
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 200,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertEqual(params['response_type'], ['code'])
                self.assertEqual(
                    params['scope'][0].split(' '), ['r_basicprofile', 'r_emailaddress'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
            except (KeyError, AssertionError) as e:
                returnQuery = urllib.parse.urlencode({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnQuery = urllib.parse.urlencode({
                    'state': state,
                    'code': providerInfo['accounts'][self.accountType]['auth_code']
                })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (params['redirect_uri'][0], returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc='^www.linkedin.com$',
                          path='^/uas/oauth2/accessToken$', method='POST')
        def mockLinkedinToken(url, request):
            try:
                self.assertEqual(
                    request.headers['Content-Type'], 'application/x-www-form-urlencoded')
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['grant_type'], ['authorization_code'])
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e),
                        'error_description': repr(e)
                    })
                }
            try:
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'error': repr(e),
                        'error_description': repr(e)
                    })
                }
            return json.dumps({
                'access_token': account['access_token'],
                'expires_in': datetime.timedelta(days=60).seconds
            })

        @httmock.urlmatch(scheme='https', netloc='^api.linkedin.com$',
                          path=r'^/v1/people/~(?::\(.+\)?)$', method='GET')
        def mockLinkedinApi(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'Bearer %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'errorCode': 0,
                        'message': repr(e)
                    })
                }
            try:
                fieldsRe = re.match(r'^.+:\((.+)\)$', url.path)
                self.assertTrue(fieldsRe)
                self.assertSetEqual(
                    set(fieldsRe.group(1).split(',')),
                    {'id', 'emailAddress', 'firstName', 'lastName'})
                params = urllib.parse.parse_qs(url.query)
                self.assertEqual(params['format'], ['json'])
            except AssertionError as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'errorCode': 0,
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'id': account['user']['oauth']['id'],
                'firstName': account['user']['firstName'],
                'lastName': account['user']['lastName'],
                'emailAddress': account['user']['email']
            })

        with httmock.HTTMock(
            mockLinkedinRedirect,
            mockLinkedinToken,
            mockLinkedinApi,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)

    def testBitbucketOauth(self):  # noqa
        providerInfo = {
            'id': 'bitbucket',
            'name': 'Bitbucket',
            'client_id': {
                'key': PluginSettings.BITBUCKET_CLIENT_ID,
                'value': 'bitbucket_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.BITBUCKET_CLIENT_SECRET,
                'value': 'bitbucket_test_client_secret'
            },
            'allowed_callback_re':
                r'^http://127\.0\.0\.1(?::\d+)?'
                r'/api/v1/oauth/bitbucket/callback$',
            'url_re': r'^https://bitbucket\.org/site/oauth2/authorize',
            'accounts': {
                'existing': {
                    'auth_code': 'bitbucket_existing_auth_code',
                    'access_token': 'bitbucket_existing_test_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'bitbucket',
                            'id': '2399'
                        }
                    }
                },
                'new': {
                    'auth_code': 'bitbucket_new_auth_code',
                    'access_token': 'bitbucket_new_test_token',
                    'user': {
                        # login may be provided externally by Bitbucket; for
                        # simplicity here, do not use a username with whitespace
                        # or underscores
                        'login': 'drago',
                        'email': 'metaphor@labs.ussr.gov',
                        'firstName': 'Ivan',
                        'lastName': 'Drago',
                        'oauth': {
                            'provider': 'bitbucket',
                            'id': 1983
                        }
                    }
                }
            }
        }

        @httmock.urlmatch(scheme='https', netloc='^bitbucket.org$',
                          path='^/site/oauth2/authorize$', method='GET')
        def mockBitbucketRedirect(url, request):
            redirectUri = None
            try:
                params = urllib.parse.parse_qs(url.query)
                # Check redirect_uri first, so other errors can still redirect
                redirectUri = params['redirect_uri'][0]
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertRegex(redirectUri, providerInfo['allowed_callback_re'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
                self.assertEqual(params['scope'], ['account'])
            except (KeyError, AssertionError) as e:
                returnQuery = urllib.parse.urlencode({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnQuery = urllib.parse.urlencode({
                    'state': state,
                    'code': providerInfo['accounts'][self.accountType]['auth_code']
                })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (redirectUri, returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc='^bitbucket.org$',
                          path='^/site/oauth2/access_token$', method='POST')
        def mockBitbucketToken(url, request):
            try:
                self.assertEqual(request.headers['Accept'], 'application/json')
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['grant_type'], ['authorization_code'])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 400,
                    'content': json.dumps({
                        'error': repr(e),
                        'error_description': repr(e)
                    })
                }
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
                self.assertRegex(
                    params['redirect_uri'][0], providerInfo['allowed_callback_re'])
            except (KeyError, AssertionError) as e:
                returnBody = json.dumps({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnBody = json.dumps({
                    'token_type': 'bearer',
                    'access_token': account['access_token'],
                    'scope': 'account'
                })
            return {
                'status_code': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'content': returnBody
            }

        @httmock.urlmatch(scheme='https', netloc='^api.bitbucket.org$',
                          path='^/2.0/user$', method='GET')
        def mockBitbucketApiUser(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'Bearer %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'created_on': '2011-12-20T16:34:07.132459+00:00',
                'uuid': account['user']['oauth']['id'],
                'location': 'Santa Monica, CA',
                'links': {},
                'website': 'https://tutorials.bitbucket.org/',
                'username': account['user']['login'],
                'display_name': '%s %s' % (
                    account['user']['firstName'], account['user']['lastName'])
            })

        @httmock.urlmatch(scheme='https', netloc='^api.bitbucket.org$',
                          path='^/2.0/user/emails$', method='GET')
        def mockBitbucketApiEmail(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'Bearer %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'page': 1,
                'pagelen': 10,
                'size': 1,
                'values': [{
                    'is_primary': True,
                    'is_confirmed': True,
                    'email': account['user']['email'],
                    'links': {},
                    'type': 'email'
                }]
            })

        with httmock.HTTMock(
            mockBitbucketRedirect,
            mockBitbucketToken,
            mockBitbucketApiUser,
            mockBitbucketApiEmail,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)

    def testBoxOauth(self):  # noqa
        providerInfo = {
            'id': 'box',
            'name': 'Box',
            'client_id': {
                'key': PluginSettings.BOX_CLIENT_ID,
                'value': 'box_test_client_id'
            },
            'client_secret': {
                'key': PluginSettings.BOX_CLIENT_SECRET,
                'value': 'box_test_client_secret'
            },
            'allowed_callback_re':
                r'^http://127\.0\.0\.1(?::\d+)?/api/v1/oauth/box/callback$',
            'url_re': r'^https://account\.box\.com/api/oauth2/authorize',
            'accounts': {
                'existing': {
                    'auth_code': 'box_existing_auth_code',
                    'access_token': 'box_existing_test_token',
                    'user': {
                        'login': self.adminUser['login'],
                        'email': self.adminUser['email'],
                        'firstName': self.adminUser['firstName'],
                        'lastName': self.adminUser['lastName'],
                        'oauth': {
                            'provider': 'box',
                            'id': '2481632'
                        }
                    }
                },
                'new': {
                    'auth_code': 'box_new_auth_code',
                    'access_token': 'box_new_test_token',
                    'user': {
                        # this login is not provided by Box, but will be
                        # created internally by _deriveLogin
                        'login': 'metaphor',
                        'email': 'metaphor@labs.ussr.gov',
                        'firstName': 'Ivan',
                        'lastName': 'Drago',
                        'oauth': {
                            'provider': 'box',
                            'id': '1985'
                        }
                    }
                }
            }
        }

        @httmock.urlmatch(scheme='https', netloc='^account.box.com$',
                          path='^/api/oauth2/authorize$', method='GET')
        def mockBoxRedirect(url, request):
            redirectUri = None
            try:
                params = urllib.parse.parse_qs(url.query)
                # Check redirect_uri first, so other errors can still redirect
                redirectUri = params['redirect_uri'][0]
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                self.assertRegex(redirectUri, providerInfo['allowed_callback_re'])
                state = params['state'][0]
                # Nothing to test for state, since provider doesn't care
            except (KeyError, AssertionError) as e:
                returnQuery = urllib.parse.urlencode({
                    'error': repr(e),
                })
            else:
                returnQuery = urllib.parse.urlencode({
                    'state': state,
                    'code': providerInfo['accounts'][self.accountType]['auth_code']
                })
            return {
                'status_code': 302,
                'headers': {
                    'Location': '%s?%s' % (redirectUri, returnQuery)
                }
            }

        @httmock.urlmatch(scheme='https', netloc='^api.box.com$',
                          path='^/oauth2/token$', method='POST')
        def mockBoxToken(url, request):
            try:
                self.assertEqual(request.headers['Accept'], 'application/json')
                params = urllib.parse.parse_qs(request.body)
                self.assertEqual(params['client_id'], [providerInfo['client_id']['value']])
            except (KeyError, AssertionError) as e:
                return {
                    'status_code': 404,
                    'content': json.dumps({
                        'error': repr(e)
                    })
                }
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if account['auth_code'] == params['code'][0]:
                        break
                else:
                    self.fail()
                self.assertEqual(params['client_secret'], [providerInfo['client_secret']['value']])
            except (KeyError, AssertionError) as e:
                returnBody = json.dumps({
                    'error': repr(e),
                    'error_description': repr(e)
                })
            else:
                returnBody = json.dumps({
                    'token_type': 'bearer',
                    'access_token': account['access_token'],
                    'scope': 'user:email'
                })
            return {
                'status_code': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'content': returnBody
            }

        @httmock.urlmatch(scheme='https', netloc='^api.box.com$',
                          path='^/2.0/users/me$', method='GET')
        def mockBoxApiUser(url, request):
            try:
                for account in six.viewvalues(providerInfo['accounts']):
                    if 'Bearer %s' % account['access_token'] == request.headers['Authorization']:
                        break
                else:
                    self.fail()
            except AssertionError as e:
                return {
                    'status_code': 401,
                    'content': json.dumps({
                        'message': repr(e)
                    })
                }
            return json.dumps({
                'id': account['user']['oauth']['id'],
                'login': account['user']['email'],
                'name': '%s %s' % (account['user']['firstName'], account['user']['lastName'])
            })

        with httmock.HTTMock(
            mockBoxRedirect,
            mockBoxToken,
            mockBoxApiUser,
            # Must keep 'mockOtherRequest' last
            self.mockOtherRequest
        ):
            self._testOauth(providerInfo)
