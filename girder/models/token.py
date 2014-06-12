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
import datetime
import hashlib
import random
import string

from girder.constants import AccessType
from .model_base import AccessControlledModel


def genToken(length=64):
    """
    Use this utility function to generate a random string of
    a desired length.
    """
    return ''.join(random.choice(string.letters + string.digits)
                   for x in range(length))


class Token(AccessControlledModel):
    """
    This model stores session tokens for user authentication.
    """
    def initialize(self):
        self.name = 'token'
        self.ensureIndex(('expires', {'expireAfterSeconds': 0}))

    def validate(self, doc):
        # TODO one validation that might be nice would be adding a maximum
        # number of tokens per user. If they exceeded the max, it would begin
        # to delete the oldest ones. We have to support multiple valid tokens
        # per user to support things like logging in from multiple machines, but
        # we can still set a sensible maximum.
        return doc

    def createToken(self, user, days=180):
        """
        Creates a new token for the user.

        :param user: The user to create the session for.
        :type user: dict
        :param days: The lifespan of the session in days.
        :type days: int
        :returns: The token document that was created.
        """
        now = datetime.datetime.now()
        token = {
            '_id': genToken(),
            'created': now,
            'userId': user['_id'],
            'expires': now + datetime.timedelta(days=days)
            }
        self.setUserAccess(token, user=user, level=AccessType.ADMIN)
        return self.save(token)
