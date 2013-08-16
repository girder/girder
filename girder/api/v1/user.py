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
import json

from ...constants import AccessType
from ..rest import Resource, RestException
from .docs import user_docs


COOKIE_LIFETIME = cherrypy.config['sessions']['cookie_lifetime']


class User(Resource):

    def _filter(self, user):
        """
        Helper to filter the user model.
        """
        return self.filterDocument(
            user, allow=['_id', 'login', 'email', 'public', 'size',
                         'firstName', 'lastName', 'admin', 'hashAlg'])

    def _sendAuthTokenCookie(self, user, token):
        """ Helper method to send the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['authToken'] = json.dumps({
            'userId': str(user['_id']),
            'token': str(token['_id'])
            })
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = COOKIE_LIFETIME * 3600 * 24

    def _deleteAuthTokenCookie(self):
        """ Helper method to kill the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['authToken'] = ''
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = 0

    def index(self, params):
        return 'todo: index'

    def login(self, params):
        """
        Login endpoint. Sends a session cookie in the response on success.

        :param login: The login name.
        :param password: The user's password.
        """
        (user, token) = self.getCurrentUser(returnToken=True)

        # Only create and send new cookie if user isn't already sending
        # a valid one.
        if not user:
            self.requireParams(['login', 'password'], params)

            login = params['login'].lower().strip()
            loginField = 'email' if '@' in login else 'login'

            cursor = self.model('user').find({loginField: login}, limit=1)
            if cursor.count() == 0:
                raise RestException('Login failed.', code=403)

            user = cursor.next()

            token = self.model('token').createToken(user, days=COOKIE_LIFETIME)
            self._sendAuthTokenCookie(user, token)

            if not self.model('password').authenticate(user,
                                                       params['password']):
                raise RestException('Login failed.', code=403)

        return {'message': 'Login succeeded.',
                'authToken': {
                    'token': token['_id'],
                    'expires': token['expires'],
                    'userId': user['_id']
                    }
                }

    def logout(self):
        self._deleteAuthTokenCookie()
        return {'message': 'Logged out.'}

    def createUser(self, params):
        self.requireParams(['firstName', 'lastName', 'login', 'password',
                            'email'], params)

        user = self.model('user').createUser(
            login=params['login'], password=params['password'],
            email=params['email'], firstName=params['firstName'],
            lastName=params['lastName'])

        token = self.model('token').createToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user, token)

        return self._filter(user)

    @Resource.endpoint
    def DELETE(self, path, params):
        """
        Delete a user account.
        """
        if not path:
            raise RestException(
                'Path parameter should be the user ID to delete.')

        user = self.getCurrentUser()
        userToDelete = self.getObjectById(
            self.model('user'), id=path[0], user=user, checkAccess=True,
            level=AccessType.ADMIN)

        self.model('user').remove(userToDelete)
        return {'message': 'Deleted user %s.' % userToDelete['login']}

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            return self.index(params)
        else:  # assume it's a user id
            user = self.getCurrentUser()
            return self._filter(self.getObjectById(
                self.model('user'), id=path[0], user=user, checkAccess=True))

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to register a new user, to login, or to logout.
        """
        if not path:
            return self.createUser(params)
        elif path[0] == 'login':
            return self.login(params)
        elif path[0] == 'logout':
            return self.logout()
        else:
            raise RestException('Unsupported operation.')
