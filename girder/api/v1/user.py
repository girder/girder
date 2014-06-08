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
import json

from ..rest import Resource, RestException, loadmodel
from ..describe import Description
from girder.constants import AccessType, SettingKey
from girder.models.token import genToken
from girder.utility import mail_utils


class User(Resource):
    """API Endpoint for users in the system."""

    def __init__(self):
        self.resourceName = 'user'
        self.COOKIE_LIFETIME = int(self.model('setting').get(
            SettingKey.COOKIE_LIFETIME, default=180))

        self.route('DELETE', ('authentication',), self.logout)
        self.route('DELETE', (':id',), self.deleteUser)
        self.route('GET', (), self.find)
        self.route('GET', ('me',), self.getMe)
        self.route('GET', ('authentication',), self.login)
        self.route('GET', (':id',), self.getUser)
        self.route('POST', (), self.createUser)
        self.route('PUT', (':id',), self.updateUser)
        self.route('PUT', ('password',), self.changePassword)
        self.route('DELETE', ('password',), self.resetPassword)

    def _sendAuthTokenCookie(self, user):
        """ Helper method to send the authentication cookie """
        token = self.model('token').createToken(user, days=self.COOKIE_LIFETIME)

        cookie = cherrypy.response.cookie
        cookie['authToken'] = json.dumps({
            'userId': str(user['_id']),
            'token': str(token['_id'])
        })
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = self.COOKIE_LIFETIME * 3600 * 24

        return token

    def _deleteAuthTokenCookie(self):
        """ Helper method to kill the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['authToken'] = ''
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = 0

    def find(self, params):
        """
        Get a list of users. You can pass a "text" parameter to filter the
        users by a full text search string.

        :param [text]: Full text search.
        :param limit: The result set size limit, default=50.
        :param offset: Offset into the results, default=0.
        :param sort: The field to sort by, default=name.
        :param sortdir: 1 for ascending, -1 for descending, default=1.
        """
        limit, offset, sort = self.getPagingParameters(params, 'lastName')
        currentUser = self.getCurrentUser()

        return [self.model('user').filter(user, currentUser)
                for user in self.model('user').search(
                    text=params.get('text'), user=currentUser,
                    offset=offset, limit=limit, sort=sort)]
    find.description = (
        Description('List or search for users.')
        .responseClass('User')
        .param('text', "Pass this to perform a full text search for items.",
               required=False)
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the user list by (default=lastName)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int'))

    @loadmodel(map={'id': 'userToGet'}, model='user', level=AccessType.READ)
    def getUser(self, userToGet, params):
        currentUser = self.getCurrentUser()
        return self.model('user').filter(userToGet, currentUser)
    getUser.description = (
        Description('Get a user by ID.')
        .responseClass('User')
        .param('id', 'The ID of the user.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403))

    def getMe(self, params):
        currentUser = self.getCurrentUser()
        return self.model('user').filter(currentUser, currentUser)
    getMe.description = (
        Description('Retrieve the currently logged-in user information.')
        .responseClass('User'))

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
            authHeader = cherrypy.request.headers.get('Authorization')

            if not authHeader or not authHeader[0:6] == 'Basic ':
                raise RestException('Use HTTP Basic Authentication', 401)

            try:
                credentials = base64.b64decode(authHeader[6:])
            except:
                raise RestException('Invalid HTTP Authorization header')

            login, password = credentials.split(':', 1)

            login = login.lower().strip()
            loginField = 'email' if '@' in login else 'login'

            cursor = self.model('user').find({loginField: login}, limit=1)
            if cursor.count() == 0:
                raise RestException('Login failed.', code=403)

            user = cursor.next()

            if not self.model('password').authenticate(user, password):
                raise RestException('Login failed.', code=403)

            setattr(cherrypy.request, 'girderUser', user)
            token = self._sendAuthTokenCookie(user)

        return {
            'user': self.model('user').filter(user, user),
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'userId': user['_id']
            },
            'message': 'Login succeeded.'
        }
    login.description = (
        Description('Log in to the system.')
        .notes('Pass your username and password using HTTP Basic Auth. Sends'
               ' a cookie that should be passed back in future requests.')
        .errorResponse('Missing Authorization header.', 401)
        .errorResponse('Invalid login or password.', 403))

    def logout(self, params):
        self._deleteAuthTokenCookie()
        return {'message': 'Logged out.'}
    logout.description = (
        Description('Log out of the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.'))

    def createUser(self, params):
        self.requireParams(
            ('firstName', 'lastName', 'login', 'password', 'email'), params)

        user = self.model('user').createUser(
            login=params['login'], password=params['password'],
            email=params['email'], firstName=params['firstName'],
            lastName=params['lastName'])
        setattr(cherrypy.request, 'girderUser', user)

        self._sendAuthTokenCookie(user)

        currentUser = self.getCurrentUser()

        return self.model('user').filter(user, currentUser)
    createUser.description = (
        Description('Create a new user.')
        .responseClass('User')
        .param('login', "The user's requested login.")
        .param('email', "The user's email address.")
        .param('firstName', "The user's first name.")
        .param('lastName', "The user's last name.")
        .param('password', "The user's requested password")
        .errorResponse('A parameter was invalid, or the specified login or'
                       ' email already exists in the system.'))

    @loadmodel(map={'id': 'userToDelete'}, model='user', level=AccessType.ADMIN)
    def deleteUser(self, userToDelete, params):
        self.model('user').remove(userToDelete)
        return {'message': 'Deleted user %s.' % userToDelete['login']}
    deleteUser.description = (
        Description('Delete a user by ID.')
        .param('id', 'The ID of the user.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to delete this user.', 403))

    @loadmodel(map={'id': 'user'}, model='user', level=AccessType.WRITE)
    def updateUser(self, user, params):
        self.requireParams(('firstName', 'lastName', 'email'), params)

        user['firstName'] = params['firstName']
        user['lastName'] = params['lastName']
        user['email'] = params['email']

        currentUser = self.getCurrentUser()
        savedUser = self.model('user').save(user)
        return self.model('user').filter(savedUser, currentUser)
    updateUser.description = (
        Description("Update a user's information.")
        .param('id', 'The ID of the user.', paramType='path')
        .param('firstName', 'First name of the user.')
        .param('lastName', 'Last name of the user.')
        .param('email', 'The email of the user.')
        .errorResponse()
        .errorResponse('You do not have write access for this user.', 403))

    def changePassword(self, params):
        self.requireParams(('old', 'new'), params)
        user = self.getCurrentUser()

        if user is None:
            raise RestException('You are not logged in.', code=401)

        if not self.model('password').authenticate(user, params['old']):
            raise RestException('Old password is incorrect.', code=403)

        self.model('user').setPassword(user, params['new'])
        return {'message': 'Password changed.'}
    changePassword.description = (
        Description('Change your password.')
        .param('old', 'Your current password.')
        .param('new', 'Your new password.')
        .errorResponse('You are not logged in.', 401)
        .errorResponse('Your old password is incorrect.', 403)
        .errorResponse('Your new password is invalid.'))

    def resetPassword(self, params):
        self.requireParams(('email',), params)
        email = params['email'].lower().strip()

        cursor = self.model('user').find({'email': email}, limit=1)
        if cursor.count() == 0:
            raise RestException('That email is not registered.')

        user = cursor.next()
        randomPass = genToken(length=12)

        html = mail_utils.renderTemplate('resetPassword.mako', {
            'password': randomPass
        })
        mail_utils.sendEmail(to=email, subject='Girder: Password reset',
                             text=html)
        self.model('user').setPassword(user, randomPass)
        return {'message': 'Sent password reset email.'}
    resetPassword.description = (
        Description('Reset a forgotten password via email.')
        .param('email', 'Your email address.')
        .errorResponse('That email does not exist in the system.'))
