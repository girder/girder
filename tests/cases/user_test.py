# -*- coding: utf-8 -*-
import cherrypy
import collections
import datetime
import re

from .. import base

from girder import events
from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User
from girder.settings import SettingKey


def setUpModule():
    base.startServer()

    User()._cryptContext.update(schemes=['plaintext'])


def tearDownModule():
    base.stopServer()


class UserTestCase(base.TestCase):
    def _verifyAuthCookie(self, resp, secure=False):
        self.assertTrue('girderToken' in resp.cookie)
        self.cookieVal = resp.cookie['girderToken'].value
        self.assertFalse(not self.cookieVal)
        lifetime = int(Setting().get(SettingKey.COOKIE_LIFETIME))
        self.assertEqual(
            resp.cookie['girderToken']['expires'],
            lifetime * 3600 * 24)
        self.assertEqual(resp.cookie['girderToken']['secure'], True if secure else '')

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

    def testRegisterAndLogin(self):
        """
        Test user registration and logging in.
        """
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

        params['password'] = 'good:password'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')

        # Make login something that violates the regex but doesn't contain @
        params['login'] = ' '
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'login')

        params['login'] = 'goodlogin'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertValidationError(resp, 'email')

        # Now successfully create the user
        params['email'] = 'good@girder.test'
        resp = self.request(path='/user', method='POST', params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)

        user = User().load(resp.json['_id'], force=True)

        # Try logging in without basic auth, should get 401
        resp = self.request(path='/user/authentication', method='GET')
        self.assertStatus(resp, 401)

        # Bad authentication header
        resp = self.request(
            path='/user/authentication', method='GET',
            additionalHeaders=[('Authorization', 'Basic Not-Valid-64')])
        self.assertStatus(resp, 401)
        self.assertEqual('Invalid HTTP Authorization header',
                         resp.json['message'])
        resp = self.request(
            path='/user/authentication', method='GET',
            additionalHeaders=[('Authorization', 'Basic NotValid')])
        self.assertStatus(resp, 401)
        self.assertEqual('Invalid HTTP Authorization header',
                         resp.json['message'])

        # Login with unregistered email
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='incorrect@girder.test:badpassword')
        self.assertStatus(resp, 401)
        self.assertEqual('Login failed.', resp.json['message'])

        # Correct email, but wrong password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='good@girder.test:badpassword')
        self.assertStatus(resp, 401)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with email
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='good@girder.test:good:password')
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ['authToken'])
        self.assertHasKeys(
            resp.json['authToken'], ['token', 'expires'])
        self._verifyAuthCookie(resp)

        # Invalid login
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='badlogin:good:password')
        self.assertStatus(resp, 401)
        self.assertEqual('Login failed.', resp.json['message'])

        # Login successfully with fallback Girder-Authorization header
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:good:password',
                            authHeader='Girder-Authorization')
        self.assertStatusOk(resp)

        # Login successfully with login
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:good:password')
        self.assertStatusOk(resp)
        self._verifyAuthCookie(resp)

        # Login with HTTPS login
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='goodlogin:good:password', useHttps=True)
        self.assertStatusOk(resp)
        self._verifyAuthCookie(resp, secure=True)

        # Test user/me
        resp = self.request(path='/user/me', method='GET', user=user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['login'], user['login'])

    def testGetAndUpdateUser(self):
        """
        Tests for the GET and PUT user endpoints.
        """
        params = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        user = User().createUser(**params)

        params['email'] = 'notasgood@girder.test'
        params['login'] = 'notasgoodlogin'
        nonAdminUser = User().createUser(**params)

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

        params['email'] = 'valid@girder.test '
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)
        self.assertEqual(resp.json['email'], 'valid@girder.test')
        self.assertEqual(resp.json['firstName'], 'NewFirst')
        self.assertEqual(resp.json['lastName'], 'New Last')

        # test admin checkbox
        params = {
            'email': 'valid@girder.test',
            'firstName': 'NewFirst ',
            'lastName': ' New Last ',
            'admin': 'true'
        }
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatusOk(resp)
        self._verifyUserDocument(resp.json)
        self.assertEqual(resp.json['admin'], True)

        # test removal of admin flag
        user = User().load(user['_id'], force=True)
        self.assertEqual(user['admin'], True)
        params = {
            'email': 'valid@girder.test',
            'firstName': 'NewFirst ',
            'lastName': ' New Last ',
            'admin': 'false'
        }
        resp = self.request(path='/user/%s' % user['_id'], method='PUT',
                            user=user, params=params)
        self.assertStatusOk(resp)
        user = User().load(resp.json['_id'], force=True)
        self.assertEqual(user['admin'], False)

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
        users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder.test' % num)
            for num in [0, 1]]

        # Create a folder and give both users some access on it
        folder = Folder().createFolder(
            parent=users[0], name='x', parentType='user', public=False,
            creator=users[0])
        Folder().setUserAccess(folder, users[0], AccessType.WRITE)
        Folder().setUserAccess(folder, users[1], AccessType.READ)
        folder = Folder().save(folder)

        self.assertEqual(len(folder['access']['users']), 2)

        # Create a token for user 1
        token = Token().createToken(users[1])

        # Create a group, and have user 1 request to join it
        group = Group().createGroup('test', users[0], public=True)
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

        users[1] = User().load(users[1]['_id'], force=True)
        folder = Folder().load(folder['_id'], force=True)
        token = Token().load(token['_id'], force=True, objectId=False)
        group = Group().load(group['_id'], force=True)

        # Make sure user and token were deleted
        self.assertEqual(users[1], None)
        self.assertEqual(token, None)

        # Make sure pending invite to group was deleted
        self.assertEqual(len(list(Group().getFullRequestList(group))), 0)

        # Make sure access control references for the user were deleted
        self.assertEqual(len(folder['access']['users']), 1)

        # Delete user 0
        resp = self.request(path='/user/%s' % users[0]['_id'], method='DELETE',
                            user=users[0])
        self.assertStatusOk(resp)

        # Make sure the user's folder was deleted
        folder = Folder().load(folder['_id'], force=True)
        self.assertEqual(folder, None)

    def testUserIndex(self):
        """
        Test user list endpoint.
        """
        # Create some users.
        for x in ('c', 'a', 'b'):
            user = User().createUser(
                'usr%s' % x, 'passwd', 'tst', '%s_usr' % x, 'u%s@girder.test' % x)
        resp = self.request(path='/user', method='GET', params={
            'limit': 2,
            'offset': 1
        }, user=user)
        self.assertStatusOk(resp)

        # Make sure the limit, order, and offset are respected, and that our
        # default sorting is by lastName.
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['lastName'], 'b_usr')
        self.assertEqual(resp.json[1]['lastName'], 'c_usr')

    def testPasswordChange(self):
        user = User().createUser('user1', 'passwd', 'tst', 'usr', 'user@girder.test')
        user2 = User().createUser('user2', 'passwd', 'tst', 'usr', 'user2@girder.test')

        # Must be logged in
        resp = self.request(path='/user/password', method='PUT', params={
            'old': 'passwd',
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
            'old': 'wrong_passwd',
            'new': 'something_else'
        }, user=user)
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Old password is incorrect.')

        # New password must meet requirements
        resp = self.request(path='/user/password', method='PUT', params={
            'old': 'passwd',
            'new': 'x'
        }, user=user)
        self.assertStatus(resp, 400)

        # Change password successfully
        resp = self.request(path='/user/password', method='PUT', params={
            'old': 'passwd',
            'new': 'something_else'
        }, user=user)
        self.assertStatusOk(resp)

        # Make sure we can login with new password
        resp = self.request(path='/user/authentication', method='GET',
                            basicAuth='user@girder.test:something_else')
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
        admin = User().createUser('admin', 'password', 'Admin', 'Admin', 'admin@girder.test')

        Setting().set(SettingKey.REGISTRATION_POLICY, 'approve')

        self.assertTrue(base.mockSmtp.isMailQueueEmpty())

        user = User().createUser('user', 'password', 'User', 'User', 'user@girder.test')

        # pop email
        self.assertTrue(base.mockSmtp.waitForMail())
        base.mockSmtp.getMail(parse=True)

        # cannot login without being approved
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatus(resp, 401)
        self.assertTrue(resp.json['extra'] == 'accountApproval')

        # ensure only admins can change status
        path = '/user/%s' % user['_id']
        resp = self.request(path=path, method='PUT', user=user, params={
            'firstName': user['firstName'],
            'lastName': user['lastName'],
            'email': user['email'],
            'status': 'enabled'
        })
        self.assertStatus(resp, 403)
        self.assertEqual(resp.json['message'], 'Only admins may change status.')

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
        self.assertStatus(resp, 401)
        self.assertEqual(resp.json['extra'], 'disabled')

    def testEmailVerification(self):
        Setting().set(SettingKey.EMAIL_VERIFICATION, 'required')

        self.assertTrue(base.mockSmtp.isMailQueueEmpty())

        User().createUser('admin', 'password', 'Admin', 'Admin', 'admin@girder.test')

        self.assertTrue(base.mockSmtp.waitForMail())
        base.mockSmtp.getMail(parse=True)

        User().createUser('user', 'password', 'User', 'User', 'user@girder.test')

        self.assertTrue(base.mockSmtp.waitForMail())
        msg = base.mockSmtp.getMail(parse=True)

        # cannot login without verifying email
        resp = self.request('/user/authentication', basicAuth='user:password')
        self.assertStatus(resp, 401)
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
        User().createUser('user1', 'passwd', 'tst', 'usr', 'user@girder.test')
        # Temporary password should require email param
        self.ensureRequiredParams(
            path='/user/password/temporary', method='PUT', required={'email'})
        # Temporary password with an incorrect email
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={'email': 'bad_email@girder.test'})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'That email is not registered.')
        # Actually generate temporary access token
        self.assertTrue(base.mockSmtp.isMailQueueEmpty())
        resp = self.request(path='/user/password/temporary', method='PUT',
                            params={'email': 'user@girder.test'})
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
        # Checking if a token is a valid temporary token should fail if the
        # token is missing or doesn't match the user ID
        path = '/user/password/temporary/' + userId
        self.ensureRequiredParams(path=path, required={'token'})
        resp = self.request(path=path, method='GET', params={'token': 'not valid'})
        self.assertStatus(resp, 400)
        resp = self.request(path=path, method='GET', params={'token': tokenId})
        self.assertStatusOk(resp)
        user = resp.json['user']

        # We should have a real auth token now
        self.assertTrue('girderToken' in resp.cookie)
        authToken = resp.cookie['girderToken'].value
        token = Token().load(authToken, force=True, objectId=False)
        self.assertEqual(str(token['userId']), userId)
        self.assertFalse(Token().hasScope(token, [
            TokenScope.TEMPORARY_USER_AUTH
        ]))
        self.assertTrue(Token().hasScope(token, [
            TokenScope.USER_AUTH
        ]))

        # Artificially adjust the token to have expired.
        token = Token().load(tokenId, force=True, objectId=False)
        token['expires'] = (datetime.datetime.utcnow()
                            - datetime.timedelta(days=1))
        Token().save(token)
        resp = self.request(path=path, method='GET', params={'token': tokenId})
        self.assertStatus(resp, 401)

        # We should now be able to change the password
        resp = self.request(path='/user/password', method='PUT', params={
            'old': tokenId,
            'new': 'another_password'
        }, user=user)
        self.assertStatusOk(resp)

        # The token should have been deleted
        token = Token().load(tokenId, force=True, objectId=False)
        self.assertEqual(token, None)

    def testUserCreation(self):
        admin = User().createUser('user1', 'passwd', 'tst', 'usr', 'user@girder.test')
        self.assertTrue(admin['admin'])

        # Close registration
        Setting().set(SettingKey.REGISTRATION_POLICY, 'closed')

        params = {
            'email': 'some.email@girder.test',
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
            'email': 'other.email@girder.test',
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
        Setting().set(SettingKey.USER_DEFAULT_FOLDERS, 'public_private')
        user1 = User().createUser('folderuser1', 'passwd', 'tst', 'usr', 'folderuser1@girder.test')
        user1Folders = Folder().find({
            'parentId': user1['_id'],
            'parentCollection': 'user'})
        self.assertSetEqual(
            set(folder['name'] for folder in user1Folders),
            {'Public', 'Private'}
        )

        # User should be able to see that 2 folders exist
        resp = self.request(path='/user/%s/details' % user1['_id'], user=user1)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 2)

        # Anonymous users should only see 1 folder exists
        resp = self.request(path='/user/%s/details' % user1['_id'])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 1)

        Setting().set(SettingKey.USER_DEFAULT_FOLDERS, 'none')
        user2 = User().createUser(
            'folderuser2', 'mypass', 'First', 'Last', 'folderuser2@girder.test')
        user2Folders = Folder().find({
            'parentId': user2['_id'],
            'parentCollection': 'user'})
        self.assertSetEqual(
            set(folder['name'] for folder in user2Folders),
            set()
        )

    def testAdminFlag(self):
        admin = User().createUser('user1', 'passwd', 'tst', 'usr', 'user@girder.test')
        self.assertTrue(admin['admin'])

        params = {
            'email': 'some.email@girder.test',
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
            user = User().createUser(
                login='myuser', password='passwd', firstName='A', lastName='A',
                email='email@girder.test')
            self.assertEqual(count['created'], 1)

            count = collections.defaultdict(int)
            with events.bound('model.user.save', 'test', preSave), \
                    events.bound('model.user.save.after', 'test', postSave):
                user = User().save(user, triggerEvents=False)
                self.assertEqual(count['pre'], 0)
                self.assertEqual(count['created'], 0)
                self.assertEqual(count['post'], 0)

                count = collections.defaultdict(int)
                User().save(user)
                self.assertEqual(count['pre'], 1)
                self.assertEqual(count['created'], 0)
                self.assertEqual(count['post'], 1)

    def testPrivateUser(self):
        """
        Make sure private users behave correctly.
        """
        # Create an admin user
        User().createUser(
            firstName='Admin', lastName='Admin', login='admin',
            email='admin@admin.com', password='adminadmin')

        # Register a private user (non-admin)
        pvt = User().createUser(
            firstName='Guy', lastName='Noir', login='guynoir',
            email='guy.noir@girder.test', password='guynoir', public=False)

        self.assertEqual(pvt['public'], False)

        folder = next(Folder().childFolders(parentType='user', parent=pvt))

        # Private users should be able to upload files
        resp = self.request(path='/item', method='POST', user=pvt, params={
            'name': 'foo.txt',
            'folderId': folder['_id']
        })
        self.assertStatusOk(resp)
        itemId = resp.json['_id']

        file = self.uploadFile('hi.txt', 'hello', user=pvt, parent=resp.json, parentType='item')
        self.assertEqual(str(file['itemId']), itemId)

    def testUsersDetails(self):
        """
        Test that the user count is correct.
        """
        # Create an admin user
        admin = User().createUser(
            firstName='Admin', lastName='Admin', login='admin',
            email='admin@admin.com', password='adminadmin')
        # Create a couple of users
        users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder.test' % num, public=False)
            for num in [0, 1]]
        resp = self.request(path='/user/details', user=admin, method='GET')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nUsers'], 3)
        # test for a non-admin user
        resp = self.request(path='/user/details', user=users[0], method='GET')
        self.assertStatusOk(resp)
        # will find the public admin user and the user itself
        self.assertEqual(resp.json['nUsers'], 2)
        # test for a non-user
        resp = self.request(path='/user/details', method='GET')
        self.assertStatus(resp, 401)
