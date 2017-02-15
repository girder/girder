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

import base64
import cherrypy
import datetime

from ..describe import Description, autoDescribeRoute
from girder.api import access
from girder.api.rest import Resource, RestException, AccessException, filtermodel, setCurrentUser
from girder.constants import AccessType, SettingKey, TokenScope
from girder.models.token import genToken
from girder.utility import mail_utils


class User(Resource):
    """API Endpoint for users in the system."""

    def __init__(self):
        super(User, self).__init__()
        self.resourceName = 'user'

        self.route('DELETE', ('authentication',), self.logout)
        self.route('DELETE', (':id',), self.deleteUser)
        self.route('GET', (), self.find)
        self.route('GET', ('me',), self.getMe)
        self.route('GET', ('authentication',), self.login)
        self.route('GET', (':id',), self.getUser)
        self.route('GET', (':id', 'details'), self.getUserDetails)
        self.route('POST', (), self.createUser)
        self.route('PUT', (':id',), self.updateUser)
        self.route('PUT', ('password',), self.changePassword)
        self.route('PUT', (':id', 'password'), self.changeUserPassword)
        self.route('GET', ('password', 'temporary', ':id'),
                   self.checkTemporaryPassword)
        self.route('PUT', ('password', 'temporary'),
                   self.generateTemporaryPassword)
        self.route('DELETE', ('password',), self.resetPassword)
        self.route('PUT', (':id', 'verification'), self.verifyEmail)
        self.route('POST', ('verification',), self.sendVerificationEmail)

    @access.public
    @filtermodel(model='user')
    @autoDescribeRoute(
        Description('List or search for users.')
        .responseClass('User', array=True)
        .param('text', "Pass this to perform a full text search for items.", required=False)
        .pagingParams(defaultSort='lastName')
    )
    def find(self, text, limit, offset, sort, params):
        return list(self.model('user').search(
            text=text, user=self.getCurrentUser(), offset=offset, limit=limit, sort=sort))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model='user')
    @autoDescribeRoute(
        Description('Get a user by ID.')
        .responseClass('User')
        .modelParam('id', model='user', level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def getUser(self, user, params):
        return user

    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model='user')
    @autoDescribeRoute(
        Description('Retrieve the currently logged-in user information.')
        .responseClass('User')
    )
    def getMe(self, params):
        return self.getCurrentUser()

    @access.public
    @autoDescribeRoute(
        Description('Log in to the system.')
        .notes('Pass your username and password using HTTP Basic Auth. Sends'
               ' a cookie that should be passed back in future requests.')
        .errorResponse('Missing Authorization header.', 401)
        .errorResponse('Invalid login or password.', 403)
    )
    def login(self, params):
        user, token = self.getCurrentUser(returnToken=True)

        # Only create and send new cookie if user isn't already sending a valid one.
        if not user:
            authHeader = cherrypy.request.headers.get('Girder-Authorization')

            if not authHeader:
                authHeader = cherrypy.request.headers.get('Authorization')

            if not authHeader or not authHeader[0:6] == 'Basic ':
                raise RestException('Use HTTP Basic Authentication', 401)

            try:
                credentials = base64.b64decode(authHeader[6:]).decode('utf8')
                if ':' not in credentials:
                    raise TypeError
            except Exception:
                raise RestException('Invalid HTTP Authorization header', 401)

            login, password = credentials.split(':', 1)
            user = self.model('user').authenticate(login, password)

            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)

        return {
            'user': self.model('user').filter(user, user),
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'scope': token['scope']
            },
            'message': 'Login succeeded.'
        }

    @access.user
    @autoDescribeRoute(
        Description('Log out of the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.')
    )
    def logout(self, params):
        token = self.getCurrentToken()
        if token:
            self.model('token').remove(token)
        self.deleteAuthTokenCookie()
        return {'message': 'Logged out.'}

    @access.public
    @filtermodel(model='user', addFields={'authToken'})
    @autoDescribeRoute(
        Description('Create a new user.')
        .responseClass('User')
        .param('login', "The user's requested login.")
        .param('email', "The user's email address.")
        .param('firstName', "The user's first name.")
        .param('lastName', "The user's last name.")
        .param('password', "The user's requested password")
        .param('admin', 'Whether this user should be a site administrator.',
               required=False, dataType='boolean', default=False)
        .errorResponse('A parameter was invalid, or the specified login or'
                       ' email already exists in the system.')
    )
    def createUser(self, login, email, firstName, lastName, password, admin, params):
        currentUser = self.getCurrentUser()

        regPolicy = self.model('setting').get(SettingKey.REGISTRATION_POLICY)

        if not currentUser or not currentUser['admin']:
            admin = False
            if regPolicy == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')

        user = self.model('user').createUser(
            login=login, password=password, email=email, firstName=firstName,
            lastName=lastName, admin=admin)

        if not currentUser and self.model('user').canLogin(user):
            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)
            user['authToken'] = {
                'token': token['_id'],
                'expires': token['expires']
            }
        return user

    @access.user
    @autoDescribeRoute(
        Description('Delete a user by ID.')
        .modelParam('id', model='user', level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to delete this user.', 403)
    )
    def deleteUser(self, user, params):
        self.model('user').remove(user)
        return {'message': 'Deleted user %s.' % user['login']}

    @access.user
    @filtermodel(model='user')
    @autoDescribeRoute(
        Description("Update a user's information.")
        .modelParam('id', model='user', level=AccessType.WRITE)
        .param('firstName', 'First name of the user.')
        .param('lastName', 'Last name of the user.')
        .param('email', 'The email of the user.')
        .param('admin', 'Is the user a site admin (admin access required)',
               required=False, dataType='boolean')
        .param('status', 'The account status (admin access required)',
               required=False, enum=('pending', 'enabled', 'disabled'))
        .errorResponse()
        .errorResponse(('You do not have write access for this user.',
                        'Must be an admin to create an admin.'), 403)
    )
    def updateUser(self, user, firstName, lastName, email, admin, status, params):
        user['firstName'] = firstName
        user['lastName'] = lastName
        user['email'] = email

        # Only admins can change admin state
        if admin is True:
            if self.getCurrentUser()['admin']:
                user['admin'] = admin
            elif not user['admin']:
                raise AccessException('Only admins may enable admin state.')

        # Only admins can change status
        if status is not None and status != user.get('status', 'enabled'):
            if not self.getCurrentUser()['admin']:
                raise AccessException('Only admins may change status.')
            if user['status'] == 'pending' and status == 'enabled':
                # Send email on the 'pending' -> 'enabled' transition
                self.model('user')._sendApprovedEmail(user)
            user['status'] = status

        return self.model('user').save(user)

    @access.admin
    @autoDescribeRoute(
        Description('Change a user\'s password.')
        .notes('Only administrators may use this endpoint.')
        .modelParam('id', model='user', level=AccessType.ADMIN)
        .param('password', 'The user\'s new password.')
        .errorResponse('You are not an administrator.', 403)
        .errorResponse('The new password is invalid.')
    )
    def changeUserPassword(self, user, password, params):
        self.model('user').setPassword(user, password)
        return {'message': 'Password changed.'}

    @access.user
    @autoDescribeRoute(
        Description('Change your password.')
        .param('old', 'Your current password or a temporary access token.')
        .param('new', 'Your new password.')
        .errorResponse(('You are not logged in.',
                        'Your old password is incorrect.'), 401)
        .errorResponse('Your new password is invalid.')
    )
    def changePassword(self, old, new, params):
        user = self.getCurrentUser()
        token = None

        if not old:
            raise RestException('Old password must not be empty.')

        if (not self.model('password').hasPassword(user) or
                not self.model('password').authenticate(user, old)):
            # If not the user's actual password, check for temp access token
            token = self.model('token').load(old, force=True, objectId=False, exc=False)
            if (not token or not token.get('userId') or
                    token['userId'] != user['_id'] or
                    not self.model('token').hasScope(
                        token, TokenScope.TEMPORARY_USER_AUTH)):
                raise AccessException('Old password is incorrect.')

        self.model('user').setPassword(user, new)

        if token:
            # Remove the temporary access token if one was used
            self.model('token').remove(token)

        return {'message': 'Password changed.'}

    @access.public
    @autoDescribeRoute(
        Description('Reset a forgotten password via email.')
        .param('email', 'Your email address.', strip=True)
        .errorResponse('That email does not exist in the system.')
    )
    def resetPassword(self, email, params):
        user = self.model('user').findOne({'email': email.lower()})
        if user is None:
            raise RestException('That email is not registered.')

        randomPass = genToken(length=12)

        html = mail_utils.renderTemplate('resetPassword.mako', {
            'password': randomPass
        })
        mail_utils.sendEmail(to=email, subject='Girder: Password reset', text=html)
        self.model('user').setPassword(user, randomPass)
        return {'message': 'Sent password reset email.'}

    @access.public
    @autoDescribeRoute(
        Description('Create a temporary access token for a user.  The user\'s '
                    'password is not changed.')
        .param('email', 'Your email address.', strip=True)
        .errorResponse('That email does not exist in the system.')
    )
    def generateTemporaryPassword(self, email, params):
        user = self.model('user').findOne({'email': email.lower()})

        if not user:
            raise RestException('That email is not registered.')

        token = self.model('token').createToken(
            user, days=1, scope=TokenScope.TEMPORARY_USER_AUTH)

        url = '%s#useraccount/%s/token/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))

        html = mail_utils.renderTemplate('temporaryAccess.mako', {
            'url': url,
            'token': str(token['_id'])
        })
        mail_utils.sendEmail(to=email, subject='Girder: Temporary access', text=html)
        return {'message': 'Sent temporary access email.'}

    @access.public
    @autoDescribeRoute(
        Description('Check if a specified token is a temporary access token '
                    'for the specified user.  If the token is valid, returns '
                    'information on the token and user.')
        .modelParam('id', 'The user ID to check.', model='user', force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token does not grant temporary access to the specified user.', 401)
    )
    def checkTemporaryPassword(self, user, token, params):
        token = self.model('token').load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = self.model('token').hasScope(token, TokenScope.TEMPORARY_USER_AUTH)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token does not grant temporary access to this user.')

        # Temp auth is verified, send an actual auth token now. We keep the
        # temp token around since it can still be used on a subsequent request
        # to change the password
        authToken = self.sendAuthTokenCookie(user)

        return {
            'user': self.model('user').filter(user, user),
            'authToken': {
                'token': authToken['_id'],
                'expires': authToken['expires'],
                'temporary': True
            },
            'message': 'Temporary access token is valid.'
        }

    @access.public
    @autoDescribeRoute(
        Description('Get detailed information about a user.')
        .modelParam('id', model='user', level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the user.', 403)
    )
    def getUserDetails(self, user, params):
        return {
            'nFolders': self.model('user').countFolders(
                user, filterUser=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.public
    @autoDescribeRoute(
        Description('Verify an email address using a token.')
        .modelParam('id', 'The user ID to check.', model='user', force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token is invalid or expired.', 401)
    )
    def verifyEmail(self, user, token, params):
        token = self.model('token').load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = self.model('token').hasScope(token, TokenScope.EMAIL_VERIFICATION)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token is invalid or expired.')

        user['emailVerified'] = True
        self.model('token').remove(token)
        user = self.model('user').save(user)

        if self.model('user').canLogin(user):
            setCurrentUser(user)
            authToken = self.sendAuthTokenCookie(user)
            return {
                'user': self.model('user').filter(user, user),
                'authToken': {
                    'token': authToken['_id'],
                    'expires': authToken['expires'],
                    'scope': authToken['scope']
                },
                'message': 'Email verification succeeded.'
            }
        else:
            return {
                'user': self.model('user').filter(user, user),
                'message': 'Email verification succeeded.'
            }

    @access.public
    @autoDescribeRoute(
        Description('Send verification email.')
        .param('login', 'Your login or email address.', strip=True)
        .errorResponse('That login is not registered.', 401)
    )
    def sendVerificationEmail(self, login, params):
        loginField = 'email' if '@' in login else 'login'
        user = self.model('user').findOne({loginField: login.lower()})

        if not user:
            raise RestException('That login is not registered.', 401)

        self.model('user')._sendVerificationEmail(user)
        return {'message': 'Sent verification email.'}
