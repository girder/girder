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
def admin(fun, scope=None, cookie=False):
    """
    REST endpoints that require administrator access should be wrapped in this decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str or None
    :param cookie: if True, this rest endpoint allows the use of a cookie for
        authentication.  If this is specified on routes that can alter the
        system (those other than HEAD and GET), it can expose an application to
        Cross-Site Request Forgery (CSRF) attacks.
    :type cookie: bool
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        rest.requireAdmin(rest.getCurrentUser())
        return fun(*args, **kwargs)
    wrapped.accessLevel = 'admin'
    wrapped.requiredScopes = scope
    if cookie:
        wrapped.cookieAuth = True
    return wrapped


@optionalArgumentDecorator
def user(fun, scope=None, cookie=False):
    """
    REST endpoints that require a logged-in user should be wrapped with this access decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: To also expose this endpoint for certain token scopes,
        pass those scopes here. If multiple are passed, all will be required.
    :type scope: str or list of str or None
    :param cookie: if True, this rest endpoint allows the use of a cookie for
        authentication.  If this is specified on routes that can alter the
        system (those other than HEAD and GET), it can expose an application to
        Cross-Site Request Forgery (CSRF) attacks.
    :type cookie: bool
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        if not rest.getCurrentUser():
            raise AccessException('You must be logged in.')
        return fun(*args, **kwargs)
    wrapped.accessLevel = 'user'
    wrapped.requiredScopes = scope
    if cookie:
        wrapped.cookieAuth = True
    return wrapped


@optionalArgumentDecorator
def token(fun, scope=None, required=False, cookie=False):
    """
    REST endpoints that require a token, but not necessarily a user authentication token, should use
    this access decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: The scope or list of scopes required for this token.
    :type scope: str or list of str or None
    :param required: Whether all of the passed ``scope`` are required to access the endpoint at all.
    :type required: bool
    :param cookie: if True, this rest endpoint allows the use of a cookie for
        authentication.  If this is specified on routes that can alter the
        system (those other than HEAD and GET), it can expose an application to
        Cross-Site Request Forgery (CSRF) attacks.
    :type cookie: bool
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
    if cookie:
        wrapped.cookieAuth = True
    return wrapped


@optionalArgumentDecorator
def public(fun, scope=None, cookie=False):
    """
    Functions that allow any client access, including those that haven't logged
    in should be wrapped in this decorator.

    :param fun: A REST endpoint.
    :type fun: callable
    :param scope: The scope or list of scopes required for this token.
    :type scope: str or list of str or None
    :param cookie: if True, this rest endpoint allows the use of a cookie for
        authentication.  If this is specified on routes that can alter the
        system (those other than HEAD and GET), it can expose an application to
        Cross-Site Request Forgery (CSRF) attacks.
    :type cookie: bool
    """
    fun.accessLevel = 'public'
    fun.requiredScopes = scope
    if cookie:
        fun.cookieAuth = True
    return fun
