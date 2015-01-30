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

import functools

from girder.models.model_base import AccessException
from girder.api import rest


def admin(fun):
    """
    Functions that require administrator access should be wrapped in this
    decorator.
    """
    @functools.wraps(fun)
    def accessDecorator(*args, **kwargs):
        rest.requireAdmin(rest.getCurrentUser())
        return fun(*args, **kwargs)
    accessDecorator.accessLevel = 'admin'
    return accessDecorator


def user(fun):
    """
    Functions that allow any user (not just administrators) should be wrapped
    in this decorator. That is, a token must be passed that has the
    "core.user_auth" scope and a valid user ID.
    """
    @functools.wraps(fun)
    def accessDecorator(*args, **kwargs):
        user = rest.getCurrentUser()
        if not user:
            raise AccessException('You must be logged in.')
        return fun(*args, **kwargs)
    accessDecorator.accessLevel = 'user'
    return accessDecorator


def public(fun):
    """
    Functions that allow any client access, including those that haven't logged
    in should be wrapped in this decorator.
    """
    @functools.wraps(fun)
    def accessDecorator(*args, **kwargs):
        return fun(*args, **kwargs)
    accessDecorator.accessLevel = 'public'
    return accessDecorator


def token(fun):
    """
    Functions that require a token, but not necessarily a user authentication
    token, should use this access decorator. This will ensure a valid token
    was passed, but checking of the scopes is left to the handler and is not
    part of this decorator.
    """
    @functools.wraps(fun)
    def accessDecorator(*args, **kwargs):
        token = rest.getCurrentToken()
        if not token:
            raise AccessException('You must be logged in or supply a valid '
                                  'session token.')
        return fun(*args, **kwargs)
    accessDecorator.accessLevel = 'token'
    return accessDecorator
