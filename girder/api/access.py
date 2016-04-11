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

import six

from girder.api import rest
from girder.models.model_base import AccessException


def admin(*args, **kwargs):
    """
    Functions that require administrator access should be wrapped in this
    decorator.

    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str
    """
    if len(args) == 1 and callable(args[0]):  # Raw decorator
        @six.wraps(args[0])
        def wrapped(*iargs, **ikwargs):
            rest.requireAdmin(rest.getCurrentUser())
            return args[0](*iargs, **ikwargs)
        wrapped.accessLevel = 'admin'
        return wrapped
    else:  # We should return a decorator
        def dec(fun):
            @six.wraps(fun)
            def wrapped(*iargs, **ikwargs):
                rest.requireAdmin(rest.getCurrentUser())
                return fun(*iargs, **ikwargs)
            wrapped.accessLevel = 'admin'
            wrapped.requiredScopes = kwargs.get('scope')
            return wrapped
        return dec


def user(*args, **kwargs):
    """
    Functions that require a logged-in user should be wrapped with this access
    decorator.

    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str
    """
    if len(args) == 1 and callable(args[0]):  # Raw decorator
        @six.wraps(args[0])
        def wrapped(*iargs, **ikwargs):
            if not rest.getCurrentUser():
                raise AccessException('You must be logged in.')
            return args[0](*iargs, **ikwargs)
        wrapped.accessLevel = 'user'
        return wrapped
    else:  # We should return a decorator
        def dec(fun):
            @six.wraps(fun)
            def wrapped(*iargs, **ikwargs):
                if not rest.getCurrentUser():
                    raise AccessException('You must be logged in.')
                return fun(*iargs, **ikwargs)
            wrapped.accessLevel = 'user'
            wrapped.requiredScopes = kwargs.get('scope')
            return wrapped
        return dec


def token(*args, **kwargs):
    """
    Functions that require a token, but not necessarily a user authentication
    token, should use this access decorator.

    :param scope: The scope or list of scopes required for this token.
    :type scope: str or list of str
    """
    if len(args) == 1 and callable(args[0]):  # Raw decorator
        @six.wraps(args[0])
        def wrapped(*iargs, **ikwargs):
            if not rest.getCurrentToken():
                raise AccessException(
                    'You must be logged in or have a valid auth token.')
            return args[0](*iargs, **ikwargs)
        wrapped.accessLevel = 'token'
        return wrapped
    else:  # We should return a decorator
        def dec(fun):
            @six.wraps(fun)
            def wrapped(*iargs, **ikwargs):
                if not rest.getCurrentToken():
                    raise AccessException(
                        'You must be logged in or have a valid auth token.')
                return fun(*iargs, **ikwargs)
            wrapped.accessLevel = 'token'
            wrapped.requiredScopes = kwargs.get('scope')
            return wrapped
        return dec


def public(*args, **kwargs):
    """
    Functions that allow any client access, including those that haven't logged
    in should be wrapped in this decorator.
    """
    if len(args) == 1 and callable(args[0]):  # Raw decorator
        args[0].accessLevel = 'public'
        return args[0]
    else:  # We should return a decorator
        def dec(fun):
            fun.accessLevel = 'public'
            fun.requiredScopes = kwargs.get('scope')
            return fun
        return dec


def cookie(*args, **kwargs):
    """
    REST endpoints that allow the use of a cookie for authentication should be
    wrapped in this decorator.

    When used as a normal decorator, this is only effective on endpoints for
    HEAD and GET routes (as these routes should be read-only in a RESTful API).

    While allowing cookie authentication on other types of routes exposes an
    application to Cross-Site Request Forgery (CSRF) attacks, an optional
    ``force=True`` kwarg may be passed to the decorator to make it effective
    on any type of route.
    """
    if len(args) == 1 and callable(args[0]):  # Used as a raw decorator
        force = False
        args[0].cookieAuth = (True, force)
        return args[0]
    else:  # Used with arguments
        def decorator(fun):
            fun.cookieAuth = (True, kwargs.get('force', False))
            return fun

        return decorator
