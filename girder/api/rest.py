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
import json
import six
import sys
import traceback

from . import docs
from girder import events, logger
from girder.constants import SettingKey, TerminalColor, TokenScope, SortDir
from girder.models.model_base import AccessException, GirderException, \
    ValidationException
from girder.utility.model_importer import ModelImporter
from girder.utility import config, JsonEncoder
from six.moves import range, urllib


def getUrlParts(url=None):
    """
    Calls `urllib.parse.urlparse`_ on a URL.

    :param url: A URL, or None to use the current request's URL.
    :type url: str or None
    :return: The URL's seperate components.
    :rtype: `urllib.parse.ParseResult`_

    .. note:: This is compatible with both Python 2 and 3.

    .. _urllib.parse.urlparse: https://docs.python.org/3/library/
       urllib.parse.html#urllib.parse.urlparse

    .. _urllib.parse.ParseResult: https://docs.python.org/3/library/
       urllib.parse.html#urllib.parse.ParseResult
    """
    url = url or cherrypy.url()
    return urllib.parse.urlparse(url)


def getApiUrl(url=None):
    """
    In a request thread, call this to get the path to the root of the REST API.
    The returned path does *not* end in a forward slash.

    :param url: URL from which to extract the base URL. If not specified, uses
        `cherrypy.url()`
    """
    url = url or cherrypy.url()
    idx = url.find('/api/v1')

    if idx < 0:
        raise GirderException('Could not determine API root in %s.' % url)

    return url[:idx + 7]


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
        except AccessException:
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


def getBodyJson():
    """
    For requests that are expected to contain a JSON body, this returns the
    parsed value, or raises a :class:`girder.api.rest.RestException` for
    invalid JSON.
    """
    try:
        return json.loads(cherrypy.request.body.read().decode('utf8'))
    except ValueError:
        raise RestException('Invalid JSON passed in request body.')


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
    :param force:
    :type force: bool
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
            raise RestException('No ID parameter passed: ' + idParam)

    def __call__(self, fun):
        @six.wraps(fun)
        def wrapped(*args, **kwargs):
            for raw, converted in six.viewitems(self.map):
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
                              separators=(',', ': '), cls=JsonEncoder)
            resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
            resp = '<div style="font-family:monospace;">%s</div>' % resp
            return resp.encode('utf8')

    # Default behavior will just be normal JSON output. Keep this
    # outside of the loop body in case no Accept header is passed.
    cherrypy.response.headers['Content-Type'] = 'application/json'
    return json.dumps(val, sort_keys=True, cls=JsonEncoder).encode('utf8')


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
    @six.wraps(fun)
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

            # If this is a partial response, we set the status appropriately
            if 'Content-Range' in cherrypy.response.headers:
                cherrypy.response.status = 206

            if callable(val):
                # If the endpoint returned anything callable (function,
                # lambda, functools.partial), we assume it's a generator
                # function for a streaming response.
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
        except Exception:
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
        if isinstance(scope, six.string_types):
            scope = (scope,)
        raise AccessException(
            'Invalid token scope.\nRequired: {}.\nAllowed: {}'
            .format(' '.join(scope),
                    ' '.join(tokenModel.getAllowedScopes(token))))


def _setCommonCORSHeaders():
    """
    Set CORS headers that should be passed back with either a preflight OPTIONS
    or a simple CORS request. We set these headers anytime there is an Origin
    header present since browsers will simply ignore them if the request is not
    cross-origin.
    """
    if not cherrypy.request.headers.get('origin'):
        # If there is no origin header, this is not a cross origin request
        return

    origins = ModelImporter.model('setting').get(SettingKey.CORS_ALLOW_ORIGIN)
    if origins:
        cherrypy.response.headers['Access-Control-Allow-Origin'] = origins
        cherrypy.response.headers['Access-Control-Allow-Credentials'] = 'true'


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
        self.message = message

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
        for i in range(len(nLengthRoutes)):
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
            print(TerminalColor.warning(
                'WARNING: No description docs present for route {} {}'
                .format(method, routePath)))

        # Warn if there is no access decorator on the handler function
        if not hasattr(handler, 'accessLevel'):
            routePath = '/'.join([resource] + list(route))
            print(TerminalColor.warning(
                'WARNING: No access level specified for route {} {}'
                .format(method, routePath)))

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
        for i in range(len(nLengthRoutes)):
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
        for i in range(len(a)):
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

        .. note:: You will normally not need to call this method directly, as it
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
                                       kwargs, pre=self._defaultAccess)
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
        if isinstance(required, six.string_types):
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
                            defaultSortDir=SortDir.ASCENDING):
        """
        Pass the URL parameters into this function if the request is for a
        list of resources that should be paginated. It will return a tuple of
        the form (limit, offset, sort) whose values should be passed directly
        into the model methods that are finding the resources. If the client
        did not pass the parameters, this always uses the same defaults of
        limit=50, offset=0, sort='name', sortdir=SortDir.ASCENDING=1.

        :param params: The URL query parameters.
        :type params: dict
        :param defaultSortField: If the client did not pass a 'sort' parameter,
            set this to choose a default sort field. If None, the results will
            be returned unsorted.
        :type defaultSortField: str or None
        :param defaultSortDir: Sort direction.
        :tyep defaultSortDir: girder.constants.SortDir
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

    def getBodyJson(self):
        """
        Bound wrapper for :func:`girder.api.rest.getBodyJson`.
        """
        return getBodyJson()

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

    # This is NOT wrapped in an endpoint decorator; we don't want that behavior
    def OPTIONS(self, *path, **param):
        _setCommonCORSHeaders()
        cherrypy.lib.caching.expires(0)

        allowHeaders = self.model('setting').get(SettingKey.CORS_ALLOW_HEADERS)
        allowMethods = self.model('setting').get(SettingKey.CORS_ALLOW_METHODS)\
                       or 'GET, POST, PUT, HEAD, DELETE'

        cherrypy.response.headers['Access-Control-Allow-Methods'] = allowMethods
        cherrypy.response.headers['Access-Control-Allow-Headers'] = allowHeaders

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

    @staticmethod
    def _defaultAccess(handler, **kwargs):
        """
        This is the pre-event handler callback for the events that are triggered
        before default handling of a REST request. Since such an event handler
        could accidentally circumvent the access level of the default handler,
        we enforce that handlers of these event types must also specify their
        own access level, or else default to the strictest level (admin) just
        like the core route handlers. This allows plugins to potentially
        override the default level, but makes sure they don't accidentally lower
        the access level for a given route.
        """
        if not hasattr(handler, 'accessLevel'):
            requireAdmin(getCurrentUser())


# An instance of Resource that can be shared by boundHandlers for efficiency
_sharedContext = Resource()


class boundHandler(object):
    """
    This decorator allows unbound functions to be conveniently added as route
    handlers to existing :py:class:`girder.api.rest.Resource` instances.
    With no arguments, this uses a shared, generic ``Resource`` instance as the
    context. If you need a specific instance, pass that as the ``ctx`` arg, for
    instance if you need to reference the resource name or any other properties
    specific to a Resource subclass.

    Plugins that add new routes to existing API resources are encouraged to use
    this to gain access to bound convenience methods like ``self.model``,
    ``self.boolParam``, ``self.requireParams``, etc.
    """
    def __init__(self, ctx=None):
        self.ctx = ctx or _sharedContext

    def __call__(self, fn):
        @six.wraps(fn)
        def wrapped(*args, **kwargs):
            return fn(self.ctx, *args, **kwargs)
        return wrapped
