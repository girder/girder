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
from girder.exceptions import AccessException
from girder.models.token import Token
from girder.utility import optionalArgumentDecorator


@optionalArgumentDecorator
def admin(fun, scope=None):
    """
    REST endpoints that require administrator access should be wrapped in this decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str or None
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        rest.requireAdmin(rest.getCurrentUser())
        return fun(*args, **kwargs)
    wrapped.accessLevel = 'admin'
    wrapped.requiredScopes = scope
    return wrapped


@optionalArgumentDecorator
def user(fun, scope=None):
    """
    REST endpoints that require a logged-in user should be wrapped with this access decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str or None
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        if not rest.getCurrentUser():
            raise AccessException('You must be logged in.')
        return fun(*args, **kwargs)
    wrapped.accessLevel = 'user'
    wrapped.requiredScopes = scope
    return wrapped


@optionalArgumentDecorator
def token(fun, scope=None, required=False):
    """
    REST endpoints that require a token, but not necessarily a user authentication token, should use
    this access decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: The scope or list of scopes required for this token.
    :type scope: str or list of str or None
    :param required: Whether all of the passed ``scope`` are required to access the endpoint at all.
    :type required: bool
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        if not rest.getCurrentToken():
            raise AccessException('You must be logged in or have a valid auth token.')
        if required:
            Token().requireScope(rest.getCurrentToken(), scope)
        return fun(*args, **kwargs)
    wrapped.accessLevel = 'token'
    wrapped.requiredScopes = scope
    return wrapped


@optionalArgumentDecorator
def public(fun, scope=None):
    """
    Functions that allow any client access, including those that haven't logged
    in should be wrapped in this decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: The scope or list of scopes required for this token.
    :type scope: str or list of str or None
    """
    fun.accessLevel = 'public'
    fun.requiredScopes = scope
    return fun


@optionalArgumentDecorator
def cookie(fun, force=False):
    """
    REST endpoints that allow the use of a cookie for authentication should be
    wrapped in this decorator.

    When used as a normal decorator, this is only effective on endpoints for
    HEAD and GET routes (as these routes should be read-only in a RESTful API).

    While allowing cookie authentication on other types of routes exposes an
    application to Cross-Site Request Forgery (CSRF) attacks, an optional
    ``force=True`` kwarg may be passed to the decorator to make it effective
    on any type of route.

    :param fun: A REST endpoint.
    :type fun: callable
    :param force: Allow this to apply to non-GET and non-HEAD endpoints.
    :type force: bool
    """
    fun.cookieAuth = (True, force)
    return fun
