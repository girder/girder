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
import collections
import datetime
import functools
import json
import pymongo
import sys
import traceback
import types

from . import docs
from girder import events, logger
from girder.constants import SettingKey, TerminalColor, TokenScope
from girder.models.model_base import AccessException, GirderException, \
    ValidationException
from girder.utility.model_importer import ModelImporter
from girder.utility import config


def _cacheAuthUser(fun):
    """
    This decorator for getCurrentUser ensures that the authentication procedure
    is only performed once per request, and is cached on the request for
    subsequent calls to getCurrentUser().
    """
    def inner(returnToken=False, *args, **kwargs):
        if not returnToken and hasattr(cherrypy.request, 'girderUser'):
            return cherrypy.request.girderUser

        user = fun(returnToken, *args, **kwargs)
        if type(user) is tuple:
            setattr(cherrypy.request, 'girderUser', user[0])
        else:
            setattr(cherrypy.request, 'girderUser', user)

        return user
    return inner


def _cacheAuthToken(fun):
    """
    This decorator for getCurrentToken ensures that the token lookup
    is only performed once per request, and is cached on the request for
    subsequent calls to getCurrentToken().
    """
    def inner(*args, **kwargs):
        if hasattr(cherrypy.request, 'girderToken'):
            return cherrypy.request.girderToken

        token = fun(*args, **kwargs)
        setattr(cherrypy.request, 'girderToken', token)

        return token
    return inner


@_cacheAuthToken
def getCurrentToken(allowCookie=False):
    """
    Returns the current valid token object that was passed via the token header
    or parameter, or None if no valid token was passed.

    :param allowCookie: Normally, authentication via cookie is disallowed to
        protect against CSRF attacks. If you want to expose an endpoint that can
        be authenticated with a token passed in the Cookie, set this to True.
        This should only be used on read-only operations that will not make any
        changes to data on the server, and only in cases where the user agent
        behavior makes passing custom headers infeasible, such as downloading
        data to disk in the browser.
    :type allowCookie: bool
    """
    tokenStr = None
    if 'token' in cherrypy.request.params:  # Token as a parameter
        tokenStr = cherrypy.request.params.get('token')
    elif 'Girder-Token' in cherrypy.request.headers:
        tokenStr = cherrypy.request.headers['Girder-Token']
    elif allowCookie and 'girderToken' in cherrypy.request.cookie:
        tokenStr = cherrypy.request.cookie['girderToken'].value

    if not tokenStr:
        return None

    return ModelImporter.model('token').load(tokenStr, force=True,
                                             objectId=False)


@_cacheAuthUser
def getCurrentUser(returnToken=False):
    """
    Returns the currently authenticated user based on the token header or
    parameter.

    :param returnToken: Whether we should return a tuple that also contains the
                        token.
    :type returnToken: bool
    :returns: the user document from the database, or None if the user is not
              logged in or the token is invalid or expired.  If
              returnToken=True, returns a tuple of (user, token).
    """
    event = events.trigger('auth.user.get')
    if event.defaultPrevented and len(event.responses) > 0:
        return event.responses[0]

    token = getCurrentToken()

    def retVal(user, token):
        if returnToken:
            return (user, token)
        else:
            return user

    if (token is None or token['expires'] < datetime.datetime.utcnow() or
            'userId' not in token):
        return retVal(None, token)
    else:
        try:
            ensureTokenScopes(token, TokenScope.USER_AUTH)
        except:
            return retVal(None, token)
        user = ModelImporter.model('user').load(token['userId'], force=True)
        return retVal(user, token)


def requireAdmin(user):
    """
    Calling this on a user will ensure that they have admin rights.  If not,
    raises an AccessException.

    :param user: The user to check admin flag on.
    :type user: dict.
    :raises AccessException: If the user is not an administrator.
    """
    if user is None or user.get('admin', False) is not True:
        raise AccessException('Administrator access required.')


class loadmodel(object):
    """
    This is a decorator that can be used to load a model based on an ID param.
    For access controlled models, it will check authorization for the current
    user. The underlying function is called with a modified set of keyword
    arguments that is transformed by the "map" parameter of this decorator.

    :param map: Map of incoming parameter name to corresponding model arg name.
        If None is passed, this will map the parameter named "id" to a kwarg
        named the same as the "model" parameter.
    :type map: dict or None
    :param model: The model name, e.g. 'folder'
    :type model: str
    :param plugin: Plugin name, if loading a plugin model.
    :type plugin: str
    :param level: Access level, if this is an access controlled model.
    :type level: AccessType
    """
    def __init__(self, map=None, model=None, plugin='_core', level=None,
                 force=False):
        if map is None:
            self.map = {'id': model}
        else:
            self.map = map

        self.model = ModelImporter.model(model, plugin)
        self.level = level
        self.force = force

    def _getIdValue(self, kwargs, idParam):
        if idParam in kwargs:
            return kwargs.pop(idParam)
        elif idParam in kwargs['params']:
            return kwargs['params'].pop(idParam)
        else:
            raise GirderException('No ID parameter passed: ' + idParam,
                                  'girder.api.rest.no-id')

    def __call__(self, fun):
        @functools.wraps(fun)
        def wrapped(*args, **kwargs):
            for raw, converted in self.map.iteritems():
                id = self._getIdValue(kwargs, raw)

                if self.force:
                    kwargs[converted] = self.model.load(id, force=True)
                elif self.level is not None:
                    kwargs[converted] = self.model.load(
                        id=id, level=self.level, user=getCurrentUser())
                else:
                    kwargs[converted] = self.model.load(id)

                if kwargs[converted] is None:
                    raise RestException('Invalid {} id ({}).'
                                        .format(self.model.name, id))

            return fun(*args, **kwargs)
        return wrapped


def _createResponse(val):
    """
    Helper that encodes the response according to the requested "Accepts"
    header from the client. Currently supports "application/json" and
    "text/html".
    """
    accepts = cherrypy.request.headers.elements('Accept')
    for accept in accepts:
        if accept.value == 'application/json':
            break
        elif accept.value == 'text/html':  # pragma: no cover
            # Pretty-print and HTML-ify the response for the browser
            cherrypy.response.headers['Content-Type'] = 'text/html'
            resp = json.dumps(val, indent=4, sort_keys=True,
                              separators=(',', ': '), default=str)
            resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
            resp = '<div style="font-family:monospace;">%s</div>' % resp
            return resp

    # Default behavior will just be normal JSON output. Keep this
    # outside of the loop body in case no Accept header is passed.
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps(val, sort_keys=True, default=str)


def endpoint(fun):
    """
    REST HTTP method endpoints should use this decorator. It converts the return
    value of the underlying method to the appropriate output format and
    sets the relevant response headers. It also handles RestExceptions,
    which are 400-level exceptions in the REST endpoints, AccessExceptions
    resulting from access denial, and also handles any unexpected errors
    using 500 status and including a useful traceback in those cases.

    If you want a streamed response, simply return a generator function
    from the inner method.
    """
    @functools.wraps(fun)
    def endpointDecorator(self, *args, **kwargs):
        # Note that the cyclomatic complexity of this function crosses our
        # flake8 configuration threshold.  Because it is largely exception
        # handling, I think that breaking it into smaller functions actually
        # reduces readability and maintainability.  To work around this, some
        # simple branches have been marked to be skipped in the cyclomatic
        # analysis.
        _setCommonCORSHeaders()
        cherrypy.lib.caching.expires(0)
        try:
            val = fun(self, args, kwargs)

            if isinstance(val, types.FunctionType):
                # If the endpoint returned a function, we assume it's a
                # generator function for a streaming response.
                cherrypy.response.stream = True
                return val()
            if isinstance(val, cherrypy.lib.file_generator):
                # Don't do any post-processing of static files
                return val

        except RestException as e:
            # Handle all user-error exceptions from the rest layer
            cherrypy.response.status = e.code
            val = {'message': e.message, 'type': 'rest'}
            if e.extra is not None:
                val['extra'] = e.extra
        except AccessException as e:
            # Permission exceptions should throw a 401 or 403, depending
            # on whether the user is logged in or not
            if self.getCurrentUser() is None:
                cherrypy.response.status = 401
            else:
                cherrypy.response.status = 403
                logger.exception('403 Error')
            val = {'message': e.message, 'type': 'access'}
        except GirderException as e:
            # Handle general girder exceptions
            logger.exception('500 Error')
            cherrypy.response.status = 500
            val = {'message': e.message, 'type': 'girder'}
            if e.identifier is not None:
                val['identifier'] = e.identifier
        except ValidationException as e:
            cherrypy.response.status = 400
            val = {'message': e.message, 'type': 'validation'}
            if e.field is not None:
                val['field'] = e.field
        except cherrypy.HTTPRedirect:  # flake8: noqa
            raise
        except:
            # These are unexpected failures; send a 500 status
            logger.exception('500 Error')
            cherrypy.response.status = 500
            t, value, tb = sys.exc_info()
            val = {'message': '%s: %s' % (t.__name__, repr(value)),
                   'type': 'internal'}
            curConfig = config.getConfig()
            if curConfig['server']['mode'] != 'production':
                # Unless we are in production mode, send a traceback too
                val['trace'] = traceback.extract_tb(tb)

        return _createResponse(val)
    return endpointDecorator


def ensureTokenScopes(token, scope):
    """
    Call this to validate a token scope for endpoints that require tokens
    other than a user authentication token. Raises an AccessException if the
    required scopes are not allowed by the given token.

    :param token: The token object used in the request.
    :type token: dict
    :param scope: The required scope or set of scopes.
    :type scope: str or list of str
    """
    tokenModel = ModelImporter.model('token')
    if not tokenModel.hasScope(token, scope):
        setattr(cherrypy.request, 'girderUser', None)
        if isinstance(scope, basestring):
            scope = (scope,)
        raise AccessException(
            'Invalid token scope.\nRequired: {}.\nAllowed: {}'
            .format(' '.join(scope),
                    ' '.join(tokenModel.getAllowedScopes(token))))


def _setCommonCORSHeaders(isOptions=False):
    """
    CORS requires that we specify the allowed origins on both the preflight
    request via OPTIONS and on the actual request.  Unless the default setting
    for allowed origin is changed, we don't support CORS.  We can permit
    multiple origins, including * to allow all origins.  Even in the wildcard
    case, we report just the requesting origin (if there is one), so as not to
    advertise the openness of the system.

    In general, see
    https://developer.mozilla.org/en-US/docs/Web/HTTP/Access_control_CORS
    for details.

    :param isOptions: True if this call is from the options method
    """
    origin = cherrypy.request.headers.get('origin', '').rstrip('/')
    if not origin:
        if isOptions:
            raise cherrypy.HTTPError(405)
        return
    cherrypy.response.headers['Access-Control-Allow-Origin'] = origin
    cherrypy.response.headers['Vary'] = 'Origin'
    # Some requests do not require further checking
    if (cherrypy.request.method in ('GET', 'HEAD') or (
            cherrypy.request.method == 'POST' and cherrypy.request.headers.get(
            'Content-Type', '') in ('application/x-www-form-urlencoded',
                                    'multipart/form-data', 'text/plain'))):
        return
    cors = ModelImporter.model('setting').corsSettingsDict()
    base = cherrypy.request.base.rstrip('/')
    # We want to handle X-Forwarded-Host be default
    altbase = cherrypy.request.headers.get('X-Forwarded-Host', '')
    if altbase:
        altbase = '%s://%s' % (cherrypy.request.scheme, altbase)
        logAltBase = ', forwarded base origin is ' + altbase
    else:
        altbase = base
        logAltBase = ''
    # If we don't have any allowed origins, return that OPTIONS isn't a
    # valid method.  If the request specified an origin, fail.
    if not cors['allowOrigin']:
        if isOptions:
            logger.info('CORS 405 error: no allowed origins (request origin '
                        'is %s, base origin is %s%s', origin, base, logAltBase)
            raise cherrypy.HTTPError(405)
        if origin not in (base, altbase):
            logger.info('CORS 403 error: no allowed origins (request origin '
                        'is %s, base origin is %s%s', origin, base, logAltBase)
            raise cherrypy.HTTPError(403)
        return
    # If this origin is not allowed, return an error
    if ('*' not in cors['allowOrigin'] and origin not in cors['allowOrigin']
            and origin not in (base, altbase)):
        if isOptions:
            logger.info('CORS 405 error: origin not allowed (request origin '
                        'is %s, base origin is %s%s', origin, base, logAltBase)
            raise cherrypy.HTTPError(405)
        logger.info('CORS 403 error: origin not allowed (request origin '
                    'is %s, base origin is %s%s', origin, base, logAltBase)
        raise cherrypy.HTTPError(403)
    # If possible, send back the requesting origin.
    if origin not in (base, altbase) and not isOptions:
        _validateCORSMethodAndHeaders(cors)


def _validateCORSMethodAndHeaders(cors):
    """
    When processing a CORS request for a method other than OPTIONS, check to
    make sure that the method has not been restricted and that no unapproved
    headers have been sent.  Note that GET, HEAD, and POST are always allowed
    (provided, for POST, the an appropriate Content-Type is specified).

    :param cors: cors settings dictionary.
    """
    # Check if we are restricting methods
    if cors['allowMethods']:
        if cherrypy.request.method not in cors['allowMethods']:
            logger.info('CORS 403 error: method %s not allowed',
                        cherrypy.request.method)
            raise cherrypy.HTTPError(403)
    # Check if we were sent any unapproved headers
    for header in cherrypy.request.headers.keys():
        if header.lower() not in cors['allowHeaders']:
            logger.info('CORS 403 error: header %s not allowed', header)
            raise cherrypy.HTTPError(403)


class RestException(Exception):
    """
    Throw a RestException in the case of any sort of incorrect
    request (i.e. user/client error). Login and permission failures
    should set a 403 code; almost all other validation errors
    should use status 400, which is the default.
    """
    def __init__(self, message, code=400, extra=None):
        self.code = code
        self.extra = extra

        Exception.__init__(self, message)


class Resource(ModelImporter):
    """
    All REST resources should inherit from this class, which provides utilities
    for adding resources/routes to the REST API.
    """
    exposed = True

    def route(self, method, route, handler, nodoc=False, resource=None):
        """
        Define a route for your REST resource.

        :param method: The HTTP method, e.g. 'GET', 'POST', 'PUT', 'PATCH'
        :type method: str
        :param route: The route, as a list of path params relative to the
            resource root. Elements of this list starting with ':' are assumed
            to be wildcards.
        :type route: tuple
        :param handler: The method to be called if the route and method are
            matched by a request. Wildcards in the route will be expanded and
            passed as kwargs with the same name as the wildcard identifier.
        :type handler: function
        :param nodoc: If your route intentionally provides no documentation,
            set this to True to disable the warning on startup.

        :type nodoc: bool
        :param resource: The name of the resource at the root of this route.
        """
        if not hasattr(self, '_routes'):
            self._routes = collections.defaultdict(
                lambda: collections.defaultdict(list))

        # Insertion sort to maintain routes in required order.
        nLengthRoutes = self._routes[method.lower()][len(route)]
        for i in xrange(0, len(nLengthRoutes)):
            if self._shouldInsertRoute(route, nLengthRoutes[i][0]):
                nLengthRoutes.insert(i, (route, handler))
                break
        else:
            nLengthRoutes.append((route, handler))

        # Now handle the api doc if the handler has any attached
        if resource is None and hasattr(self, 'resourceName'):
            resource = self.resourceName
        elif resource is None:
            resource = handler.__module__.rsplit('.', 1)[-1]

        if hasattr(handler, 'description'):
            if handler.description is not None:
                docs.addRouteDocs(
                    resource=resource, route=route, method=method,
                    info=handler.description.asDict(), handler=handler)
        elif not nodoc:
            routePath = '/'.join([resource] + list(route))
            print TerminalColor.warning(
                'WARNING: No description docs present for route {} {}'
                .format(method, routePath))

        # Warn if there is no access decorator on the handler function
        if not hasattr(handler, 'accessLevel'):
            routePath = '/'.join([resource] + list(route))
            print TerminalColor.warning(
                'WARNING: No access level specified for route {} {}'
                .format(method, routePath))

    def removeRoute(self, method, route, handler=None, resource=None):
        """
        Remove a route from the handler and documentation.

        :param method: The HTTP method, e.g. 'GET', 'POST', 'PUT'
        :type method: str
        :param route: The route, as a list of path params relative to the
                      resource root. Elements of this list starting with ':'
                      are assumed to be wildcards.
        :type route: list
        :param handler: The method called for the route; this is necessary to
                        remove the documentation.
        :type handler: function
        :param resource: the name of the resource at the root of this route.
        """
        if not hasattr(self, '_routes'):
            return
        nLengthRoutes = self._routes[method.lower()][len(route)]
        for i in xrange(0, len(nLengthRoutes)):
            if nLengthRoutes[i][0] == route:
                del nLengthRoutes[i]
                break
        # Remove the api doc
        if resource is None and hasattr(self, 'resourceName'):
            resource = self.resourceName
        elif resource is None:
            resource = handler.__module__.rsplit('.', 1)[-1]
        if handler and hasattr(handler, 'description'):
            if handler.description is not None:
                docs.removeRouteDocs(
                    resource=resource, route=route, method=method,
                    info=handler.description.asDict(), handler=handler)

    def _shouldInsertRoute(self, a, b):
        """
        Return bool representing whether route a should go before b. Checks by
        comparing each token in order and making sure routes with literals in
        forward positions come before routes with wildcards in those positions.
        """
        for i in xrange(0, len(a)):
            if a[i][0] != ':' and b[i][0] == ':':
                return True
        return False

    def handleRoute(self, method, path, params):
        """
        Match the requested path to its corresponding route, and calls the
        handler for that route with the appropriate kwargs. If no route
        matches the path requested, throws a RestException.

        This method fires two events for each request if a matching route is
        found. The names of these events are derived from the route matched by
        the request. As an example, if the user calls GET /api/v1/item/123,
        the following two events would be fired:

            ``rest.get.item/:id.before``

        would be fired prior to calling the default API function, and

            ``rest.get.item/:id.after``

        would be fired after the route handler returns. The query params are
        passed in the info of the before and after event handlers as
        event.info['params'], and the matched route tokens are passed in
        as dict items of event.info, so in the previous example event.info would
        also contain an 'id' key with the value of 123. For endpoints with empty
        sub-routes, the trailing slash is omitted from the event name, e.g.:

            ``rest.post.group.before``

        Note: You will normally not need to call this method directly, as it
        is called by the internals of this class during the routing process.

        :param method: The HTTP method of the current request.
        :type method: str
        :param path: The path params of the request.
        :type path: list
        """
        if not self._routes:
            raise Exception('No routes defined for resource')

        method = method.lower()

        for route, handler in self._routes[method][len(path)]:
            kwargs = self._matchRoute(path, route)
            if kwargs is not False:
                if hasattr(handler, 'cookieAuth') and handler.cookieAuth:
                    getCurrentToken(allowCookie=True)

                kwargs['params'] = params
                # Add before call for the API method. Listeners can return
                # their own responses by calling preventDefault() and
                # adding a response on the event.

                if hasattr(self, 'resourceName'):
                    resource = self.resourceName
                else:
                    resource = handler.__module__.rsplit('.', 1)[-1]

                routeStr = '/'.join((resource, '/'.join(route))).rstrip('/')
                eventPrefix = '.'.join(('rest', method, routeStr))

                event = events.trigger('.'.join((eventPrefix, 'before')),
                                       kwargs)
                if event.defaultPrevented and len(event.responses) > 0:
                    val = event.responses[0]
                else:
                    self._defaultAccess(handler)
                    val = handler(**kwargs)

                # Fire the after-call event that has a chance to augment the
                # return value of the API method that was called. You can
                # reassign the return value completely by adding a response to
                # the event and calling preventDefault() on it.
                kwargs['returnVal'] = val
                event = events.trigger('.'.join((eventPrefix, 'after')), kwargs)
                if event.defaultPrevented and len(event.responses) > 0:
                    val = event.responses[0]

                return val

        raise RestException('No matching route for "{} {}"'.format(
            method.upper(), '/'.join(path)))

    def _matchRoute(self, path, route):
        """
        Helper function that attempts to match the requested path with a
        given route specification. Returns False if the requested path does
        not match the route. If it does match, this will return the dict of
        kwargs that should be passed to the underlying handler, based on the
        wildcard tokens of the route.

        :param path: The requested path.
        :type path: list
        :param route: The route specification to match against.
        :type route: list
        """
        wildcards = {}
        for i in range(0, len(route)):
            if route[i][0] == ':':  # Wildcard token
                wildcards[route[i][1:]] = path[i]
            elif route[i] != path[i]:  # Exact match token
                return False
        return wildcards

    def requireParams(self, required, provided):
        """
        Throws an exception if any of the parameters in the required iterable
        is not found in the provided parameter set.

        :param required: An iterable of required params, or if just one is
            required, you can simply pass it as a string.
        :type required: list, tuple, or str
        :param provided: The list of provided parameters.
        :type provided: dict
        """
        if isinstance(required, basestring):
            required = (required,)

        for param in required:
            if param not in provided:
                raise RestException("Parameter '%s' is required." % param)

    def boolParam(self, key, params, default=None):
        """
        Coerce a parameter value from a str to a bool. This function is case
        insensitive. The following string values will be interpreted as True:

          - ``'true'``
          - ``'on'``
          - ``'1'``
          - ``'yes'``

        All other strings will be interpreted as False. If the given param
        is not passed at all, returns the value specified by the default arg.
        """
        if key not in params:
            return default

        val = params[key]

        if type(val) is bool:
            return val

        return val.lower().strip() in ('true', 'on', '1', 'yes')

    def requireAdmin(self, user):
        """
        Calling this on a user will ensure that they have admin rights.
        If not, raises an AccessException.

        :param user: The user to check admin flag on.
        :type user: dict.
        :raises AccessException: If the user is not an administrator.
        """
        return requireAdmin(user)

    def getPagingParameters(self, params, defaultSortField=None,
                            defaultSortDir=pymongo.ASCENDING):
        """
        Pass the URL parameters into this function if the request is for a
        list of resources that should be paginated. It will return a tuple of
        the form (limit, offset, sort) whose values should be passed directly
        into the model methods that are finding the resources. If the client
        did not pass the parameters, this always uses the same defaults of
        limit=50, offset=0, sort='name', sortdir=pymongo.ASCENDING=1.

        :param params: The URL query parameters.
        :type params: dict
        :param defaultSortField: If the client did not pass a 'sort' parameter,
            set this to choose a default sort field. If None, the results will
            be returned unsorted.
        :type defaultSortField: str or None
        """
        offset = int(params.get('offset', 0))
        limit = int(params.get('limit', 50))
        sortdir = int(params.get('sortdir', defaultSortDir))

        if 'sort' in params:
            sort = [(params['sort'].strip(), sortdir)]
        elif type(defaultSortField) is str:
            sort = [(defaultSortField, sortdir)]
        else:
            sort = None

        return limit, offset, sort

    def ensureTokenScopes(self, scope):
        """
        Ensure that the token passed to this request is authorized for the
        designated scope or set of scopes. Raises an AccessException if not.

        :param scope: A scope or set of scopes that is required.
        :type scope: str or list of str
        """
        ensureTokenScopes(getCurrentToken(), scope)

    def getCurrentToken(self):
        """
        Returns the current valid token object that was passed via the token
        header or parameter, or None if no valid token was passed.
        """
        return getCurrentToken()

    def getCurrentUser(self, returnToken=False):
        """
        Returns the currently authenticated user based on the token header or
        parameter.

        :param returnToken: Whether we should return a tuple that also contains
                            the token.
        :type returnToken: bool
        :returns: The user document from the database, or None if the user
                  is not logged in or the token is invalid or expired.
                  If returnToken=True, returns a tuple of (user, token).
        """
        return getCurrentUser(returnToken)

    def sendAuthTokenCookie(self, user, scope=None):
        """ Helper method to send the authentication cookie """
        days = int(self.model('setting').get(SettingKey.COOKIE_LIFETIME))
        token = self.model('token').createToken(user, days=days, scope=scope)

        cookie = cherrypy.response.cookie
        cookie['girderToken'] = str(token['_id'])
        cookie['girderToken']['path'] = '/'
        cookie['girderToken']['expires'] = days * 3600 * 24

        return token

    def deleteAuthTokenCookie(self):
        """ Helper method to kill the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['girderToken'] = ''
        cookie['girderToken']['path'] = '/'
        cookie['girderToken']['expires'] = 0

    # This is NOT wrapped in an @endpoint decorator; we don't want that
    # behavior
    def OPTIONS(self, *path, **param):
        _setCommonCORSHeaders(True)
        cherrypy.lib.caching.expires(0)
        # Get a list of allowed methods for this path
        if not self._routes:
            raise Exception('No routes defined for resource')
        allowedMethods = ['OPTIONS']
        for routeMethod in self._routes:
            for route, handler in self._routes[routeMethod][len(path)]:
                kwargs = self._matchRoute(path, route)
                if kwargs is not False:
                    allowedMethods.append(routeMethod.upper())
                    break
        # Restrict this further if there is a user setting
        restrictMethods = self.model('setting').get(
            SettingKey.CORS_ALLOW_METHODS)
        if restrictMethods:
            restrictMethods = restrictMethods.replace(",", " ").strip() \
                .upper().split()
            allowedMethods = [method for method in allowedMethods
                              if method in restrictMethods]
        cherrypy.response.headers['Access-Control-Allow-Methods'] = \
            ', '.join(allowedMethods)
        # Send the allowed headers.
        allowHeaders = self.model('setting').get(SettingKey.CORS_ALLOW_HEADERS)
        cherrypy.response.headers['Access-Control-Allow-Headers'] = allowHeaders

        # All successful OPTIONS return 200 OK with no data
        cherrypy.response.headers['Content-Type'] = 'text/plain'
        return

    @endpoint
    def DELETE(self, path, params):
        # DELETE bodies are optional.  Assume if we have a content-length, then
        # there is a body that should be processed.
        if 'Content-Length' in cherrypy.request.headers:
            cherrypy.request.body.process()
            params.update(cherrypy.request.params)
        return self.handleRoute('DELETE', path, params)

    @endpoint
    def GET(self, path, params):
        return self.handleRoute('GET', path, params)

    @endpoint
    def POST(self, path, params):
        method = 'POST'
        # When using a POST request, the method can be overridden and really be
        # something else.  There seem to be three different 'standards' on how
        # to do this (see http://fandry.blogspot.com/2012/03/
        # x-http-header-method-override-and-rest.html).  We might as well
        # support all three.
        for key in ('X-HTTP-Method-Override', 'X-HTTP-Method',
                    'X-Method-Override'):
            if key in cherrypy.request.headers:
                method = cherrypy.request.headers[key]
        return self.handleRoute(method, path, params)

    @endpoint
    def PUT(self, path, params):
        return self.handleRoute('PUT', path, params)

    @endpoint
    def PATCH(self, path, params):
        return self.handleRoute('PATCH', path, params)

    def _defaultAccess(self, fun):
        """
        If a function wasn't wrapped by one of the security decorators, check
        the default access rights (admin required).
        """
        if not hasattr(fun, 'accessLevel'):
            self.requireAdmin(self.getCurrentUser())
