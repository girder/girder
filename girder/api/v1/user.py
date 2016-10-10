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

from ..describe import Description, describeRoute
from girder.api import access
from girder.api.rest import Resource, RestException, AccessException, filtermodel, loadmodel
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
    @describeRoute(
        Description('List or search for users.')
        .responseClass('User', array=True)
        .param('text', "Pass this to perform a full text search for items.",
               required=False)
        .pagingParams(defaultSort='lastName')
    )
    def find(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'lastName')
        return list(self.model('user').search(
            text=params.get('text'), user=self.getCurrentUser(), offset=offset,
            limit=limit, sort=sort))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @loadmodel(map={'id': 'userToGet'}, model='user', level=AccessType.READ)
    @filtermodel(model='user')
    @describeRoute(
        Description('Get a user by ID.')
        .responseClass('User')
        .param('id', 'The ID of the user.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def getUser(self, userToGet, params):
        return userToGet

    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model='user')
    @describeRoute(
        Description('Retrieve the currently logged-in user information.')
        .responseClass('User')
    )
    def getMe(self, params):
        return self.getCurrentUser()

    @access.public
    @describeRoute(
        Description('Log in to the system.')
        .notes('Pass your username and password using HTTP Basic Auth. Sends'
               ' a cookie that should be passed back in future requests.')
        .errorResponse('Missing Authorization header.', 401)
        .errorResponse('Invalid login or password.', 403)
    )
    def login(self, params):
        """
        Login endpoint. Sends an auth cookie in the response on success.
        The caller is expected to use HTTP Basic Authentication when calling
        this endpoint.
        """
        user, token = self.getCurrentUser(returnToken=True)

        # Only create and send new cookie if user isn't already sending
        # a valid one.
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

            setattr(cherrypy.request, 'girderUser', user)
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
    @describeRoute(
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
    @describeRoute(
        Description('Create a new user.')
        .responseClass('User')
        .param('login', "The user's requested login.")
        .param('email', "The user's email address.")
        .param('firstName', "The user's first name.")
        .param('lastName', "The user's last name.")
        .param('password', "The user's requested password")
        .param('admin', 'Whether this user should be a site administrator.',
               required=False, dataType='boolean')
        .errorResponse('A parameter was invalid, or the specified login or'
                       ' email already exists in the system.')
    )
    def createUser(self, params):
        self.requireParams(
            ('firstName', 'lastName', 'login', 'password', 'email'), params)

        currentUser = self.getCurrentUser()

        regPolicy = self.model('setting').get(SettingKey.REGISTRATION_POLICY)

        if currentUser is not None and currentUser['admin']:
            admin = self.boolParam('admin', params, default=False)
        else:
            admin = False
            if regPolicy == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')

        user = self.model('user').createUser(
            login=params['login'], password=params['password'],
            email=params['email'], firstName=params['firstName'],
            lastName=params['lastName'], admin=admin)

        outputUser = self.model('user').filter(user, user)
        if not currentUser and self.model('user').canLogin(user):
            setattr(cherrypy.request, 'girderUser', user)
            token = self.sendAuthTokenCookie(user)
            outputUser['authToken'] = {
                'token': token['_id'],
                'expires': token['expires']
            }
        return outputUser

    @access.user
    @loadmodel(map={'id': 'userToDelete'}, model='user', level=AccessType.ADMIN)
    @describeRoute(
        Description('Delete a user by ID.')
        .param('id', 'The ID of the user.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to delete this user.', 403)
    )
    def deleteUser(self, userToDelete, params):
        self.model('user').remove(userToDelete)
        return {'message': 'Deleted user %s.' % userToDelete['login']}

    @access.user
    @loadmodel(model='user', level=AccessType.WRITE)
    @filtermodel(model='user')
    @describeRoute(
        Description("Update a user's information.")
        .param('id', 'The ID of the user.', paramType='path')
        .param('firstName', 'First name of the user.')
        .param('lastName', 'Last name of the user.')
        .param('email', 'The email of the user.')
        .param('admin', 'Is the user a site admin (admin access required)',
               required=False, dataType='boolean')
        .param('status', 'The account status (admin access required)',
               required=False, enum=['pending', 'enabled', 'disabled'])
        .errorResponse()
        .errorResponse(('You do not have write access for this user.',
                        'Must be an admin to create an admin.'), 403)
    )
    def updateUser(self, user, params):
        self.requireParams(('firstName', 'lastName', 'email'), params)

        user['firstName'] = params['firstName']
        user['lastName'] = params['lastName']
        user['email'] = params['email']

        # Only admins can change admin state
        if 'admin' in params:
            newAdminState = self.boolParam('admin', params)
            if self.getCurrentUser()['admin']:
                user['admin'] = newAdminState
            else:
                if newAdminState != user['admin']:
                    raise AccessException('Only admins may change admin state.')

        # Only admins can change status
        if 'status' in params and params['status'] != user.get('status', 'enabled'):
            if not self.getCurrentUser()['admin']:
                raise AccessException('Only admins may change status.')
            if user['status'] == 'pending' and params['status'] == 'enabled':
                # Send email on the 'pending' -> 'enabled' transition
                self.model('user')._sendApprovedEmail(user)
            user['status'] = params['status']

        user = self.model('user').save(user)
        return self.model('user').filter(user, user)

    @access.admin
    @loadmodel(model='user', level=AccessType.ADMIN)
    @describeRoute(
        Description('Change a user\'s password.')
        .notes('Only administrators may use this endpoint.')
        .param('id', 'The ID of the user.', paramType='path')
        .param('password', 'The user\'s new password.')
        .errorResponse('You are not an administrator.', 403)
        .errorResponse('The new password is invalid.')
    )
    def changeUserPassword(self, user, params):
        self.requireParams('password', params)
        self.model('user').setPassword(user, params['password'])
        return {'message': 'Password changed.'}

    @access.user
    @describeRoute(
        Description('Change your password.')
        .param('old', 'Your current password or a temporary access token.')
        .param('new', 'Your new password.')
        .errorResponse(('You are not logged in.',
                        'Your old password is incorrect.'), 401)
        .errorResponse('Your new password is invalid.')
    )
    def changePassword(self, params):
        self.requireParams(('old', 'new'), params)
        user = self.getCurrentUser()
        token = None

        if not params['old']:
            raise RestException('Old password must not be empty.')

        if (not self.model('password').hasPassword(user) or
                not self.model('password').authenticate(user, params['old'])):
            # If not the user's actual password, check for temp access token
            token = self.model('token').load(
                params['old'], force=True, objectId=False, exc=False)
            if (not token or not token.get('userId') or
                    token['userId'] != user['_id'] or
                    not self.model('token').hasScope(
                        token, TokenScope.TEMPORARY_USER_AUTH)):
                raise AccessException('Old password is incorrect.')

        self.model('user').setPassword(user, params['new'])

        if token:
            # Remove the temporary access token if one was used
            self.model('token').remove(token)

        return {'message': 'Password changed.'}

    @access.public
    @describeRoute(
        Description('Reset a forgotten password via email.')
        .param('email', 'Your email address.')
        .errorResponse('That email does not exist in the system.')
    )
    def resetPassword(self, params):
        self.requireParams('email', params)
        email = params['email'].lower().strip()

        user = self.model('user').findOne({'email': email})
        if user is None:
            raise RestException('That email is not registered.')

        randomPass = genToken(length=12)

        html = mail_utils.renderTemplate('resetPassword.mako', {
            'password': randomPass
        })
        mail_utils.sendEmail(to=email, subject='Girder: Password reset',
                             text=html)
        self.model('user').setPassword(user, randomPass)
        return {'message': 'Sent password reset email.'}

    @access.public
    @describeRoute(
        Description('Create a temporary access token for a user.  The user\'s '
                    'password is not changed.')
        .param('email', 'Your email address.')
        .errorResponse('That email does not exist in the system.')
    )
    def generateTemporaryPassword(self, params):
        self.requireParams('email', params)
        email = params['email'].lower().strip()

        user = self.model('user').findOne({'email': email})

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
        mail_utils.sendEmail(to=email, subject='Girder: Temporary access',
                             text=html)
        return {'message': 'Sent temporary access email.'}

    @access.public
    @loadmodel(model='user', force=True)
    @describeRoute(
        Description('Check if a specified token is a temporary access token '
                    'for the specified user.  If the token is valid, returns '
                    'information on the token and user.')
        .param('id', 'The user ID to check.', paramType='path')
        .param('token', 'The token to check.')
        .errorResponse('The token does not grant temporary access to the '
                       'specified user.', 401)
    )
    def checkTemporaryPassword(self, user, params):
        self.requireParams('token', params)
        token = self.model('token').load(
            params['token'], force=True, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = self.model('token').hasScope(
            token, TokenScope.TEMPORARY_USER_AUTH)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException(
                'The token does not grant temporary access to this user.')

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
    @loadmodel(model='user', level=AccessType.READ)
    @describeRoute(
        Description('Get detailed information about a user.')
        .param('id', 'The ID of the user.', paramType='path')
        .errorResponse()
        .errorResponse('Read access was denied on the user.', 403)
    )
    def getUserDetails(self, user, params):
        return {
            'nFolders': self.model('user').countFolders(
                user, filterUser=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.public
    @loadmodel(model='user', force=True)
    @describeRoute(
        Description('Verify an email address using a token.')
        .param('id', 'The user ID to check.', paramType='path')
        .param('token', 'The token to check.')
        .errorResponse('The token is invalid or expired.', 401)
    )
    def verifyEmail(self, user, params):
        self.requireParams('token', params)
        token = self.model('token').load(
            params['token'], force=True, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = self.model('token').hasScope(
            token, TokenScope.EMAIL_VERIFICATION)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token is invalid or expired.')

        user['emailVerified'] = True
        self.model('token').remove(token)
        user = self.model('user').save(user)

        if self.model('user').canLogin(user):
            setattr(cherrypy.request, 'girderUser', user)
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
    @describeRoute(
        Description('Send verification email.')
        .param('login', 'Your login or email address.')
        .errorResponse('That login is not registered.', 401)
    )
    def sendVerificationEmail(self, params):
        self.requireParams('login', params)
        login = params['login'].lower().strip()
        loginField = 'email' if '@' in login else 'login'
        user = self.model('user').findOne({loginField: login})

        if not user:
            raise RestException('That login is not registered.', 401)

        self.model('user')._sendVerificationEmail(user)
        return {'message': 'Sent verification email.'}
