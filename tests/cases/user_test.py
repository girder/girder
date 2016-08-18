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
import collections
import datetime
import re
import six

from .. import base

from girder import events
from girder.constants import AccessType, SettingKey, TokenScope


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class UserTestCase(base.TestCase):

    def _verifyAuthCookie(self, resp):
        self.assertTrue('girderToken' in resp.cookie)
        self.cookieVal = resp.cookie['girderToken'].value
        self.assertFalse(not self.cookieVal)
        lifetime = int(self.model('setting').get(SettingKey.COOKIE_LIFETIME))
        self.assertEqual(
            resp.cookie['girderToken']['expires'],
            lifetime * 3600 * 24)

    def _verifyDeletedCookie(self, resp):
        self.assertTrue('girderToken' in resp.cookie)
        self.assertEqual(resp.cookie['girderToken'].value, '')
        self.assertEqual(resp.cookie['girderToken']['expires'], 0)

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
            path='/user', method='POST', required=six.viewkeys(params))

        # Now test parameter validation
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'password')
        self.assertEqual(cherrypy.config['users']['password_description'],
                         resp.json['message'])

        params['password'] = 'good:password'
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

        # Try logging in without basic auth, should get 401
        resp = self.request(path='/user/authentication', method='GET')
        self.assertStatus(resp, 401)

        # Bad authentication header
        resp = self.request(
            path='/user/authentication', method='GET',
            additionalHeaders=[('Girder-Authorization', 'Basic Not-Valid-64')])
        self.assertStatus(resp, 401)
        self.assertEqual('Invalid HTTP Authorization header',
                         resp.json['message'])
        resp = self.request(
            path='/user/authentication', method='GET',
            additionalHeaders=[('Girder-Authorization', 'Basic NotValid')])
        self.assertStatus(resp, 401)
        self.assertEqual('Invalid HTTP Authorization header',
                         resp.json['message'])

        # Login with unregistered email
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='incorrect@email.com:badpassword')
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Correct email, but wrong password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='good@email.com:badpassword')
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with email
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='good@email.com:good:password')
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ['authToken'])
        self.assertHasKeys(
            resp.json['authToken'], ['token', 'expires'])
        self._verifyAuthCookie(resp)

        # Invalid login
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='badlogin:good:password')
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with fallback Authorization header
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:good:password',
                            authHeader='Authorization')
        self.assertStatusOk(resp)

        # Login successfully with login
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:good:password')
        self.assertStatusOk(resp)

        # Make sure we got a nice cookie
        self._verifyAuthCookie(resp)

        # Test user/me
        resp = self.request(path='/user/me', method='GET', user=user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['login'], user['login'])

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
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:badpassword')
        self.assertStatus(resp, 403)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:goodpassword')
        self.assertStatusOk(resp)
        self.assertEqual('Login succeeded.', resp.json['message'])
        self.assertEqual('good@email.com', resp.json['user']['email'])
        self._verifyUserDocument(resp.json['user'])

        # Make sure we got a nice cookie
        self._verifyAuthCookie(resp)

        token = self.model('token').load(
            self.cookieVal, objectId=False, force=True)
        self.assertEqual(str(token['userId']), resp.json['user']['_id'])

        # Hit the logout endpoint
        resp = self.request(path='/user/authentication', method='DELETE',
                            token=token['_id'])
        self._verifyDeletedCookie(resp)

        token = self.model('token').load(
            token['_id'], objectId=False, force=True)
        self.assertEqual(token, None)

    def testGetAndUpdateUser(self):
        """
        Tests for the GET and PUT user endpoints.
        """
        params = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        user = self.model('user').createUser(**params)

        params['email'] = 'notasgood@email.com'
        params['login'] = 'notasgoodlogin'
        nonAdminUser = self.model('user').createUser(**params)

        # Test that invalid objectID gives us a 400
        resp = self.request(path='/user/bad_id')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid ObjectId: bad_id')

        resp = self.request(path='/user/%s' % user['_id'])
        self._verifyUserDocument(resp.json, admin=False)

        params = {
            'email': 'bad',
            'firstName': 'NewFirst ',
            'lastName': ' New Last ',
        }
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid email address.')

        params['email'] = 'valid@email.com '
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)
        self.assertEqual(resp.json['email'], 'valid@email.com')
        self.assertEqual(resp.json['firstName'], 'NewFirst')
        self.assertEqual(resp.json['lastName'], 'New Last')

        # test admin checkbox
        params = {
            'email': 'valid@email.com',
            'firstName': 'NewFirst ',
            'lastName': ' New Last ',
            'admin': 'true'
        }
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)
        self.assertEqual(resp.json['admin'], True)

        # test admin flag as non-admin
        params['admin'] = 'true'
        resp = self.request(path='/user/%s' % nonAdminUser['_id'],
                            method='PUT', user=nonAdminUser, params=params)
        self.assertStatus(resp, 403)

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

        # Create a token for user 1
        token = self.model('token').createToken(users[1])

        # Create a group, and have user 1 request to join it
        group = self.model('group').createGroup('test', users[0], public=True)
        resp = self.request(path='/group/%s/member' % group['_id'],
                            method='POST', user=users[1])
        self.assertStatusOk(resp)

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
        group = self.model('group').load(group['_id'], force=True)

        # Make sure user and token were deleted
        self.assertEqual(users[1], None)
        self.assertEqual(token, None)

        # Make sure pending invite to group was deleted
        self.assertEqual(
            len(list(self.model('group').getFullRequestList(group))), 0)

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
        for x in ('c', 'a', 'b'):
            self.model('user').createUser(
                'usr%s' % x, 'passwd', 'tst', '%s_usr' % x, 'u%s@u.com' % x)
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

    def testPasswordChangeAndReset(self):
        user = self.model('user').createUser('user1', 'passwd', 'tst', 'usr',
                                             'user@user.com')
        user2 = self.model('user').createUser('user2', 'passwd', 'tst', 'usr',
                                              'user2@user.com')

        # Reset password should require email param
        resp = self.request(path='/user/password', method='DELETE', params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], "Parameter 'email' is required.")

        # Reset email with an incorrect email
        resp = self.request(path='/user/password', method='DELETE', params={
            'email': 'bad_email@user.com'
        })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], "That email is not registered.")

        # Actually reset password
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        resp = self.request(path='/user/password', method='DELETE', params={
            'email': 'user@user.com'
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'], "Sent password reset email.")

        # Old password should no longer work
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='user@user.com:passwd')
        self.assertStatus(resp, 403)

        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail(parse=True)
        body = msg.get_payload(decode=True).decode('utf8')

        # Pull out the auto-generated password from the email
        search = re.search('Your new password is: <b>(.*)</b>', body)
        newPass = search.group(1)

        # Login with the new password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='user@user.com:' + newPass)
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ('authToken',))
        self.assertHasKeys(
            resp.json['authToken'], ('token', 'expires'))
        self._verifyAuthCookie(resp)

        # Now test changing passwords the normal way

        # Must be logged in
        resp = self.request(path='/user/password', method='PUT', params={
            'old': newPass,
            'new': 'something_else'
        })
        self.assertStatus(resp, 401)

        # Old password must not be empty
        resp = self.request(path='/user/password', method='PUT', params={
            'old': '',
            'new': 'something_else'
        }, user=user)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Old password must not be empty.')

        # Old password must be correct
        resp = self.request(path='/user/password', method='PUT', params={
            'old': 'passwd',
            'new': 'something_else'
        }, user=user)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Old password is incorrect.')

        # New password must meet requirements
        resp = self.request(path='/user/password', method='PUT', params={
            'old': newPass,
            'new': 'x'
        }, user=user)
        self.assertStatus(resp, 400)

        # Change password successfully
        resp = self.request(path='/user/password', method='PUT', params={
            'old': newPass,
            'new': 'something_else'
        }, user=user)
        self.assertStatusOk(resp)

        # Make sure we can login with new password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='user@user.com:something_else')
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ('authToken',))
        self.assertHasKeys(
            resp.json['authToken'], ('token', 'expires'))
        self._verifyAuthCookie(resp)

        # Non-admin user should not be able to reset admin's password
        resp = self.request(path='/user/%s/password' % str(user['_id']),
                            method='PUT', user=user2, params={
                                'password': 'another password'
        })
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'],
                         'Administrator access required.')

        # Admin user should be able to reset non-admin's password
        resp = self.request(path='/user/%s/password' % str(user2['_id']),
                            method='PUT', user=user, params={
                                'password': 'foo  bar'
        })
        self.assertStatusOk(resp)

        # Make sure we can login with new password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='user2:foo  bar')
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ('authToken',))
        self.assertHasKeys(
            resp.json['authToken'], ('token', 'expires'))
        self._verifyAuthCookie(resp)

    def testAccountApproval(self):
        admin = self.model('user').createUser(
            'admin', 'password', 'Admin', 'Admin', 'admin@example.com')

        self.model('setting').set(SettingKey.REGISTRATION_POLICY, 'approve')

        self.assertTrue(base.mockSmtp.isMailQueueEmpty())

        user = self.model('user').createUser(
            'user', 'password', 'User', 'User', 'user@example.com')

        # pop email
        self.assertTrue(base.mockSmtp.waitForMail())
        base.mockSmtp.getMail(parse=True)

        # cannot login without being approved
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['extra'] == 'accountApproval')

        # approve account
        path = '/user/%s' % user['_id']
        resp = self.request(path=path, method='PUT', user=admin, params={
            'firstName': user['firstName'],
            'lastName': user['lastName'],
            'email': user['email'],
            'status': 'enabled'
        })
        self.assertStatusOk(resp)

        # pop email
        self.assertTrue(base.mockSmtp.waitForMail())
        base.mockSmtp.getMail(parse=True)

        # can now login
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatusOk(resp)

        # disable account
        path = '/user/%s' % user['_id']
        resp = self.request(path=path, method='PUT', user=admin, params={
            'firstName': user['firstName'],
            'lastName': user['lastName'],
            'email': user['email'],
            'status': 'disabled'
        })
        self.assertStatusOk(resp)

        # cannot login again
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['extra'] == 'accountApproval')

    def testEmailVerification(self):
        self.model('setting').set(SettingKey.EMAIL_VERIFICATION, 'required')

        self.assertTrue(base.mockSmtp.isMailQueueEmpty())

        self.model('user').createUser(
            'admin', 'password', 'Admin', 'Admin', 'admin@example.com')

        self.assertTrue(base.mockSmtp.waitForMail())
        base.mockSmtp.getMail(parse=True)

        self.model('user').createUser(
            'user', 'password', 'User', 'User', 'user@example.com')

        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail(parse=True)

        # cannot login without verifying email
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['extra'] == 'emailVerification')

        # get verification link
        body = msg.get_payload(decode=True).decode('utf8')
        link = re.search('<a href="(.*)">', body).group(1)
        parts = link.split('/')
        userId = parts[-3]
        token = parts[-1]

        # verify email with token
        path = '/user/' + userId + '/verification'
        resp = self.request(path=path, method='PUT', params={'token': token})
        self.assertStatusOk(resp)

        # can now login
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatusOk(resp)

    def testTemporaryPassword(self):
        self.model('user').createUser('user1', 'passwd', 'tst', 'usr',
                                      'user@user.com')
        # Temporary password should require email param
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], "Parameter 'email' is required.")
        # Temporary password with an incorrect email
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={'email': 'bad_email@user.com'})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], "That email is not registered.")
        # Actually generate temporary access token
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={'email': 'user@user.com'})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'], "Sent temporary access email.")
        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail(parse=True)
        # Pull out the auto-generated token from the email
        body = msg.get_payload(decode=True).decode('utf8')
        search = re.search('<a href="(.*)">', body)
        link = search.group(1)
        linkParts = link.split('/')
        userId = linkParts[-3]
        tokenId = linkParts[-1]
        # Checking if a token is a valid temporary token should fail if the
        # token is missing or doesn't match the user ID
        path = '/user/password/temporary/' + userId
        resp = self.request(path=path, method='GET', params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], "Parameter 'token' is required.")
        resp = self.request(path=path, method='GET',
                            params={'token': 'not valid'})
        self.assertStatus(resp, 400)
        resp = self.request(path=path, method='GET', params={'token': tokenId})
        self.assertStatusOk(resp)
        user = resp.json['user']

        # We should have a real auth token now
        self.assertTrue('girderToken' in resp.cookie)
        authToken = resp.cookie['girderToken'].value
        token = self.model('token').load(authToken, force=True, objectId=False)
        self.assertEqual(str(token['userId']), userId)
        self.assertFalse(self.model('token').hasScope(token, [
            TokenScope.TEMPORARY_USER_AUTH
        ]))
        self.assertTrue(self.model('token').hasScope(token, [
            TokenScope.USER_AUTH
        ]))

        # Artificially adjust the token to have expired.
        token = self.model('token').load(tokenId, force=True, objectId=False)
        token['expires'] = (datetime.datetime.utcnow() -
                            datetime.timedelta(days=1))
        self.model('token').save(token)
        resp = self.request(path=path, method='GET', params={'token': tokenId})
        self.assertStatus(resp, 401)

        # We should now be able to change the password
        resp = self.request(path='/user/password', method='PUT', params={
            'old': tokenId,
            'new': 'another_password'
        }, user=user)
        self.assertStatusOk(resp)

        # The token should have been deleted
        token = self.model('token').load(tokenId, force=True, objectId=False)
        self.assertEqual(token, None)

    def testUserCreation(self):
        admin = self.model('user').createUser(
            'user1', 'passwd', 'tst', 'usr', 'user@user.com')
        self.assertTrue(admin['admin'])

        # Close registration
        self.model('setting').set(SettingKey.REGISTRATION_POLICY, 'closed')

        params = {
            'email': 'some.email@email.com',
            'login': 'otheruser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'mypass'
        }

        # Make sure we get a 400 when trying to register
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Registration on this instance is closed. Contact an '
                         'administrator to create an account for you.')

        # Admins should still be able to create users
        resp = self.request(path='/user', method='POST', params=params,
                            user=admin)
        self.assertStatusOk(resp)
        user = resp.json
        self.assertFalse(user['admin'])

        # Normal users should not be able to create new users
        resp = self.request(path='/user', method='POST', params=params,
                            user=user)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Registration on this instance is closed. Contact an '
                         'administrator to create an account for you.')

        # Admins should be able to create other admin users
        params = {
            'email': 'other.email@email.com',
            'login': 'otheruser2',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'mypass',
            'admin': True
        }
        resp = self.request(path='/user', method='POST', params=params,
                            user=admin)
        self.assertStatusOk(resp)
        self.assertTrue(resp.json['admin'])

    def testDefaultUserFolders(self):
        self.model('setting').set(SettingKey.USER_DEFAULT_FOLDERS,
                                  'public_private')
        user1 = self.model('user').createUser(
            'folderuser1', 'passwd', 'tst', 'usr', 'folderuser1@user.com')
        user1Folders = self.model('folder').find({
            'parentId': user1['_id'],
            'parentCollection': 'user'})
        self.assertSetEqual(
            set(folder['name'] for folder in user1Folders),
            {'Public', 'Private'}
        )

        # User should be able to see that 2 folders exist
        resp = self.request(path='/user/%s/details' % user1['_id'],
                            user=user1)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 2)

        # Anonymous users should only see 1 folder exists
        resp = self.request(path='/user/%s/details' % user1['_id'])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 1)

        self.model('setting').set(SettingKey.USER_DEFAULT_FOLDERS,
                                  'none')
        user2 = self.model('user').createUser(
            'folderuser2', 'mypass', 'First', 'Last', 'folderuser2@user.com')
        user2Folders = self.model('folder').find({
            'parentId': user2['_id'],
            'parentCollection': 'user'})
        self.assertSetEqual(
            set(folder['name'] for folder in user2Folders),
            set()
        )

    def testAdminFlag(self):
        admin = self.model('user').createUser(
            'user1', 'passwd', 'tst', 'usr', 'user@user.com')
        self.assertTrue(admin['admin'])

        params = {
            'email': 'some.email@email.com',
            'login': 'otheruser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'mypass',
            'admin': True
        }

        # Setting admin param to True should have no effect for normal
        # registration process
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self.assertFalse(resp.json['admin'])

    def testModelSaveHooks(self):
        """
        This tests the general correctness of the model save hooks
        """
        def preSave(event):
            count['pre'] += 1

        def createdSave(event):
            count['created'] += 1

        def postSave(event):
            count['post'] += 1

        count = collections.defaultdict(int)
        with events.bound('model.user.save.created', 'test', createdSave):
            user = self.model('user').createUser(
                login='myuser', password='passwd', firstName='A', lastName='A',
                email='email@email.com')
            self.assertEqual(count['created'], 1)

            count = collections.defaultdict(int)
            with events.bound('model.user.save', 'test', preSave), \
                    events.bound('model.user.save.after', 'test', postSave):
                user = self.model('user').save(user, triggerEvents=False)
                self.assertEqual(count['pre'], 0)
                self.assertEqual(count['created'], 0)
                self.assertEqual(count['post'], 0)

                count = collections.defaultdict(int)
                self.model('user').save(user)
                self.assertEqual(count['pre'], 1)
                self.assertEqual(count['created'], 0)
                self.assertEqual(count['post'], 1)

    def testPrivateUser(self):
        """
        Make sure private users behave correctly.
        """
        # Create an admin user
        self.model('user').createUser(
            firstName='Admin', lastName='Admin', login='admin',
            email='admin@admin.com', password='adminadmin')

        # Register a private user (non-admin)
        pvt = self.model('user').createUser(
            firstName='Guy', lastName='Noir', login='guynoir',
            email='guy.noir@email.com', password='guynoir', public=False)

        self.assertEqual(pvt['public'], False)

        folder = six.next(self.model('folder').childFolders(
            parentType='user', parent=pvt))

        # Private users should be able to upload files
        resp = self.request(path='/item', method='POST', user=pvt, params={
            'name': 'foo.txt',
            'folderId': folder['_id']
        })
        self.assertStatusOk(resp)
        itemId = resp.json['_id']

        resp = self.request(
            path='/file', method='POST', user=pvt, params={
                'parentType': 'item',
                'parentId': itemId,
                'name': 'foo.txt',
                'size': 5,
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)

        fields = [('offset', 0), ('uploadId', resp.json['_id'])]
        files = [('chunk', 'foo.txt', 'hello')]
        resp = self.multipartRequest(
            path='/file/chunk', user=pvt, fields=fields, files=files)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['itemId'], itemId)
