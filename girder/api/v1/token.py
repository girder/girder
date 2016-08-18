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

from ..rest import Resource
from ..describe import Description, describeRoute
from girder.api import access
from girder.constants import TokenScope


class Token(Resource):
    """API Endpoint for non-user tokens in the system."""

    def __init__(self):
        super(Token, self).__init__()
        self.resourceName = 'token'

        self.route('DELETE', ('session',), self.deleteSession)
        self.route('GET', ('session',), self.getSession)
        self.route('GET', ('current',), self.currentSession)
        self.route('GET', ('scopes',), self.listScopes)

    @access.public
    @describeRoute(
        Description('Retrieve the current session information.')
        .responseClass('Token')
    )
    def currentSession(self, params):
        token = self.getCurrentToken()
        return token

    @access.public
    @describeRoute(
        Description('Get an anonymous session token for the system.')
        .notes('If you are logged in, this will return a token associated '
               'with that login.')
        .responseClass('Token')
    )
    def getSession(self, params):
        """
        Create an anonymous session.  Sends an auth cookie in the response on
        success.
        """
        token = self.getCurrentToken()

        # Only create and send new cookie if token isn't valid or will expire
        # soon
        if not token:
            token = self.sendAuthTokenCookie(
                None, scope=TokenScope.ANONYMOUS_SESSION)

        return {
            'token': token['_id'],
            'expires': token['expires']
        }

    @access.token
    @describeRoute(
        Description('Remove a session from the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.')
    )
    def deleteSession(self, params):
        token = self.getCurrentToken()
        if token:
            self.model('token').remove(token)
        self.deleteAuthTokenCookie()
        return {'message': 'Session deleted.'}

    @access.public
    @describeRoute(
        Description('List all token scopes available in the system.')
    )
    def listScopes(self, params):
        return TokenScope.listScopes()
