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
from girder import events, logger, logprint
from girder.constants import SettingKey, TokenScope, SortDir
from girder.models.model_base import AccessException, GirderException, \
    ValidationException
from girder.utility.model_importer import ModelImporter
from girder.utility import config, JsonEncoder
from six.moves import range, urllib

# Arbitrary buffer length for stream-reading request bodies
READ_BUFFER_LEN = 65536


def getUrlParts(url=None):
    """
    Calls `urllib.parse.urlparse`_ on a URL.

    :param url: A URL, or None to use the current request's URL.
    :type url: str or None
    :return: The URL's separate components.
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


def iterBody(length=READ_BUFFER_LEN, strictLength=False):
    """
    This is a generator that will read the request body a chunk at a time and
    yield each chunk, abstracting details of the underlying HTTP server. This
    function works regardless of whether the body was sent with a Content-Length
    or using Transfer-Encoding: chunked, but the behavior is slightly different
    in each case.

    If `Content-Length` is provided, the `length` parameter is used to read the
    body in chunks up to size `length`. This will block until end of stream or
    the specified number of bytes is ready.

    If `Transfer-Encoding: chunked` is used, the `length` parameter is ignored
    by default, and the generator yields each chunk that is sent in the request
    regardless of its length. However, if `strictLength` is set to True, it will
    block until `length` bytes have been read or the end of the request.

    :param length: Max buffer size to read per iteration if the request has a
        known `Content-Length`.
    :type length: int
    :param strictLength: If the request is chunked, set this to True to block
        until ``length`` bytes have been read or end-of-stream.
    :type strictLength: bool
    """
    if cherrypy.request.headers.get('Transfer-Encoding') == 'chunked':
        while True:
            if strictLength:
                buf = cherrypy.request.rfile.read(length)
                if not buf:
                    break
            else:
                cherrypy.request.rfile._fetch()
                if cherrypy.request.rfile.closed:
                    break
                buf = cherrypy.request.rfile.buffer
                cherrypy.request.rfile.buffer = b''
            yield buf
    elif 'Content-Length' in cherrypy.request.headers:
        while True:
            buf = cherrypy.request.body.read(length)
            if not buf:
                break
            yield buf


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
        if isinstance(user, tuple):
            setCurrentUser(user[0])
        else:
            setCurrentUser(user)

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
            return user, token
        else:
            return user

    if (token is None or token['expires'] < datetime.datetime.utcnow() or
            'userId' not in token):
        return retVal(None, token)
    else:
        try:
            ensureTokenScopes(token, getattr(
                cherrypy.request, 'requiredScopes', TokenScope.USER_AUTH))
        except AccessException:
            return retVal(None, token)

        user = ModelImporter.model('user').load(token['userId'], force=True)
        return retVal(user, token)


def setCurrentUser(user):
    """
    Explicitly set the user for the current request thread. This can be used
    to enable specialized auth behavior on a per-request basis.

    :param user: The user to set as the current user of this request.
    :type user: dict or None
    """
    cherrypy.request.girderUser = user


def requireAdmin(user, message=None):
    """
    Calling this on a user will ensure that they have admin rights.  If not,
    raises an AccessException.

    :param user: The user to check admin flag on.
    :type user: dict.
    :param message: The exception message.
    :type message: str or None
    :raises AccessException: If the user is not an administrator.
    """
    if user is None or not user['admin']:
        raise AccessException(message or 'Administrator access required.')


def getBodyJson(allowConstants=False):
    """
    For requests that are expected to contain a JSON body, this returns the
    parsed value, or raises a :class:`girder.api.rest.RestException` for
    invalid JSON.

    :param allowConstants: Whether the keywords Infinity, -Infinity, and NaN
        should be allowed. These keywords are valid JavaScript and will parse
        to the correct float values, but are not valid in strict JSON.
    :type allowConstants: bool
    """
    if allowConstants:
        _parseConstants = None
    else:
        def _parseConstants(val):
            raise RestException('Error: "%s" is not valid JSON.' % val)

    text = cherrypy.request.body.read().decode('utf8')
    try:
        return json.loads(text, parse_constant=_parseConstants)
    except ValueError:
        raise RestException('Invalid JSON passed in request body.')


def getParamJson(name, params, default=None):
    """
    For parameters that are expected to be specified as JSON, use
    this to parse them, or raises a RestException if parsing fails.

    :param name: The param name.
    :type name: str
    :param params: The dictionary of parameters.
    :type params: dict
    :param default: The default value if no such param was passed.
    """
    if name not in params:
        return default

    try:
        return json.loads(params[name])
    except ValueError:
        raise RestException('The %s parameter must be valid JSON.' % name)


class loadmodel(ModelImporter):  # noqa: class name
    """
    This is a decorator that can be used to load a model based on an ID param.
    For access controlled models, it will check authorization for the current
    user. The underlying function is called with a modified set of keyword
    arguments that is transformed by the "map" parameter of this decorator.
    Any additional kwargs will be passed to the underlying model's `load`.

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
    :param force: Force loading of the model (skip access check).
    :type force: bool
    :param exc: Whether an exception should be raised for a nonexistent
        resource.
    :param requiredFlags: Access flags that are required on the object being loaded.
    :type requiredFlags: str or list/set/tuple of str or None
    :type exc: bool
    """
    def __init__(self, map=None, model=None, plugin='_core', level=None,
                 force=False, exc=True, requiredFlags=None, **kwargs):
        if map is None:
            self.map = {'id': model}
        else:
            self.map = map

        self.level = level
        self.force = force
        self.modelName = model
        self.plugin = plugin
        self.exc = exc
        self.kwargs = kwargs
        self.requiredFlags = requiredFlags

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
            model = self.model(self.modelName, self.plugin)

            for raw, converted in six.viewitems(self.map):
                id = self._getIdValue(kwargs, raw)

                if self.force:
                    kwargs[converted] = model.load(
                        id, force=True, **self.kwargs)
                elif self.level is not None:
                    kwargs[converted] = model.load(
                        id=id, level=self.level, user=getCurrentUser(),
                        **self.kwargs)
                else:
                    kwargs[converted] = model.load(id, **self.kwargs)

                if kwargs[converted] is None and self.exc:
                    raise RestException(
                        'Invalid %s id (%s).' % (model.name, str(id)))

                if self.requiredFlags:
                    model.requireAccessFlags(
                        kwargs[converted], user=getCurrentUser(), flags=self.requiredFlags)

            return fun(*args, **kwargs)
        return wrapped


class filtermodel(ModelImporter):  # noqa: class name
    def __init__(self, model, plugin='_core', addFields=None):
        """
        This creates a decorator that will filter a model or list of models
        returned by the wrapped function using the specified model's
        ``filter`` method. Filters the results for the user making the current
        request (i.e. the value of ``getCurrentUser()``).

        :param model: The model name.
        :type model: str
        :param plugin: The plugin name if this is a plugin model.
        :type plugin: str
        :param addFields: Extra fields (key names) that should be included in
            the returned document(s), in addition to any in the model's normal
            whitelist. Only affects top level fields.
        :type addFields: set, list, tuple, or None
        """
        self.modelName = model
        self.plugin = plugin
        self.addFields = addFields

    def __call__(self, fun):
        @six.wraps(fun)
        def wrapped(*args, **kwargs):
            val = fun(*args, **kwargs)
            if val is None:
                return None

            user = getCurrentUser()
            model = self.model(self.modelName, self.plugin)

            if isinstance(val, (list, tuple)):
                return [model.filter(m, user, self.addFields) for m in val]
            elif isinstance(val, dict):
                return model.filter(val, user, self.addFields)
            else:
                raise Exception(
                    'Cannot call filtermodel on return type: %s.' % type(val))
        return wrapped


def setRawResponse(val=True):
    """
    Normally, non-streaming responses go through a serialization process in
    accordance with the "Accept" request header. Endpoints that wish to return
    a raw response without using a streaming response should call this, or use
    its bound version on the ``Resource`` class, or add the ``rawResponse``
    decorator on the REST route handler function.

    :param val: Whether the return value should be sent raw.
    :type val: bool
    """
    cherrypy.request.girderRawResponse = val


def setResponseHeader(header, value):
    """
    Set a response header to the given value.

    :param header: The header name.
    :type header: str
    :param value: The value for the header.
    :type value: str
    """
    cherrypy.response.headers[header] = value


def rawResponse(fun):
    """
    This is a decorator that can be placed on REST route handlers, and is
    equivalent to calling ``setRawResponse()`` in the handler body.
    """
    @six.wraps(fun)
    def wrapped(*args, **kwargs):
        setRawResponse()
        return fun(*args, **kwargs)
    return wrapped


def _createResponse(val):
    """
    Helper that encodes the response according to the requested "Accepts"
    header from the client. Currently supports "application/json" and
    "text/html". If ``setRawResponse(True)`` was called on the current request
    thread, this will simply return the response raw.
    """
    if getattr(cherrypy.request, 'girderRawResponse', False) is True:
        return val

    accepts = cherrypy.request.headers.elements('Accept')
    for accept in accepts:
        if accept.value == 'application/json':
            break
        elif accept.value == 'text/html':  # pragma: no cover
            # Pretty-print and HTML-ify the response for the browser
            setResponseHeader('Content-Type', 'text/html')
            resp = json.dumps(val, indent=4, sort_keys=True, allow_nan=False,
                              separators=(',', ': '), cls=JsonEncoder)
            resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
            resp = '<div style="font-family:monospace;">%s</div>' % resp
            return resp.encode('utf8')

    # Default behavior will just be normal JSON output. Keep this
    # outside of the loop body in case no Accept header is passed.
    setResponseHeader('Content-Type', 'application/json')
    return json.dumps(val, sort_keys=True, allow_nan=False,
                      cls=JsonEncoder).encode('utf8')


def _handleRestException(e):
    # Handle all user-error exceptions from the REST layer
    cherrypy.response.status = e.code
    val = {'message': e.message, 'type': 'rest'}
    if e.extra is not None:
        val['extra'] = e.extra
    return val


def _handleAccessException(e):
    # Permission exceptions should throw a 401 or 403, depending
    # on whether the user is logged in or not
    if getCurrentUser() is None:
        cherrypy.response.status = 401
    else:
        cherrypy.response.status = 403
        logger.exception('403 Error')
    val = {'message': e.message, 'type': 'access'}
    if e.extra is not None:
        val['extra'] = e.extra
    return val


def _handleGirderException(e):
    # Handle general Girder exceptions
    logger.exception('500 Error')
    cherrypy.response.status = 500
    val = {'message': e.message, 'type': 'girder'}
    if e.identifier is not None:
        val['identifier'] = e.identifier
    return val


def _handleValidationException(e):
    cherrypy.response.status = 400
    val = {'message': e.message, 'type': 'validation'}
    if e.field is not None:
        val['field'] = e.field
    return val


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
            val = _handleRestException(e)
        except AccessException as e:
            val = _handleAccessException(e)
        except GirderException as e:
            val = _handleGirderException(e)
        except ValidationException as e:
            val = _handleValidationException(e)
        except cherrypy.HTTPRedirect:
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
    if tokenModel.hasScope(token, TokenScope.USER_AUTH):
        return

    if not tokenModel.hasScope(token, scope):
        setCurrentUser(None)
        if isinstance(scope, six.string_types):
            scope = (scope,)
        raise AccessException(
            'Invalid token scope.\n'
            'Required: %s.\n'
            'Allowed: %s' % (
                ' '.join(scope), ' '.join(tokenModel.getAllowedScopes(token))))


def _setCommonCORSHeaders():
    """
    Set CORS headers that should be passed back with either a preflight OPTIONS
    or a simple CORS request. We set these headers anytime there is an Origin
    header present since browsers will simply ignore them if the request is not
    cross-origin.
    """
    origin = cherrypy.request.headers.get('origin')
    if not origin:
        # If there is no origin header, this is not a cross origin request
        return

    allowed = ModelImporter.model('setting').get(SettingKey.CORS_ALLOW_ORIGIN)

    if allowed:
        setResponseHeader('Access-Control-Allow-Credentials', 'true')

        allowed_list = [o.strip() for o in allowed.split(',')]
        key = 'Access-Control-Allow-Origin'

        if len(allowed_list) == 1:
            setResponseHeader(key, allowed_list[0])
        elif origin in allowed_list:
            setResponseHeader(key, origin)


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

    def __init__(self):
        self._routes = collections.defaultdict(
            lambda: collections.defaultdict(list))

    def _ensureInit(self):
        """
        Calls ``Resource.__init__`` if the subclass constructor did not already
        do so.

        In the past, Resource subclasses were not expected to call their
        superclass constructor.
        """
        if not hasattr(self, '_routes'):
            Resource.__init__(self)
            logprint.warning(
                'WARNING: Resource subclass "%s" did not call '
                '"Resource__init__()" from its constructor.' %
                self.__class__.__name__)

    def route(self, method, route, handler, nodoc=False, resource=None):
        """
        Define a route for your REST resource.

        :param method: The HTTP method, e.g. 'GET', 'POST', 'PUT', 'PATCH'
        :type method: str
        :param route: The route, as a list of path params relative to the
            resource root. Elements of this list starting with ':' are assumed
            to be wildcards.
        :type route: tuple[str]
        :param handler: The method to be called if the route and method are
            matched by a request. Wildcards in the route will be expanded and
            passed as kwargs with the same name as the wildcard identifier.
        :type handler: function
        :param nodoc: If your route intentionally provides no documentation,
            set this to True to disable the warning on startup.

        :type nodoc: bool
        :param resource: The name of the resource at the root of this route.
        """
        self._ensureInit()
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
            logprint.warning(
                'WARNING: No description docs present for route %s %s' % (
                    method, routePath))

        # Warn if there is no access decorator on the handler function
        if not hasattr(handler, 'accessLevel'):
            routePath = '/'.join([resource] + list(route))
            logprint.warning(
                'WARNING: No access level specified for route %s %s' % (
                    method, routePath))

        if method.lower() not in ('head', 'get') \
            and hasattr(handler, 'cookieAuth') \
            and not (isinstance(handler.cookieAuth, tuple) and
                     handler.cookieAuth[1]):
            routePath = '/'.join([resource] + list(route))
            logprint.warning(
                'WARNING: Cannot allow cookie authentication for '
                'route %s %s without specifying "force=True"' % (
                    method, routePath))

    def removeRoute(self, method, route, handler=None, resource=None):
        """
        Remove a route from the handler and documentation.

        :param method: The HTTP method, e.g. 'GET', 'POST', 'PUT'
        :type method: str
        :param route: The route, as a list of path params relative to the
                      resource root. Elements of this list starting with ':'
                      are assumed to be wildcards.
        :type route: tuple[str]
        :param handler: The method called for the route; this is necessary to
                        remove the documentation.
        :type handler: function
        :param resource: the name of the resource at the root of this route.
        """
        self._ensureInit()
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
        if handler and getattr(handler, 'description', None) is not None:
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
            if kwargs is False:
                continue

            cherrypy.request.requiredScopes = getattr(
                handler, 'requiredScopes', None) or TokenScope.USER_AUTH

            if hasattr(handler, 'cookieAuth'):
                if isinstance(handler.cookieAuth, tuple):
                    cookieAuth, forceCookie = handler.cookieAuth
                else:
                    # previously, cookieAuth was not set by a decorator, so the
                    # legacy way must be supported too
                    cookieAuth = handler.cookieAuth
                    forceCookie = False
                if cookieAuth:
                    if forceCookie or method in ('head', 'get'):
                        # getCurrentToken will cache its output, so calling it
                        # once with allowCookie will make the parameter
                        # effectively permanent (for the request)
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

        raise RestException('No matching route for "%s %s"' % (
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

        if isinstance(val, bool):
            return val

        return val.lower().strip() in ('true', 'on', '1', 'yes')

    def requireAdmin(self, user, message=None):
        """
        Calling this on a user will ensure that they have admin rights.
        If not, raises an AccessException.

        :param user: The user to check admin flag on.
        :type user: dict.
        :param message: The exception message.
        :type message: str or None
        :raises AccessException: If the user is not an administrator.
        """
        return requireAdmin(user, message)

    def setRawResponse(self, *args, **kwargs):
        """
        Bound alias for ``girder.api.rest.setRawResponse``.
        """
        return setRawResponse(*args, **kwargs)

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
        :type defaultSortDir: girder.constants.SortDir
        """
        offset = int(params.get('offset', 0))
        limit = int(params.get('limit', 50))
        sortdir = int(params.get('sortdir', defaultSortDir))

        if 'sort' in params:
            sort = [(params['sort'].strip(), sortdir)]
        elif isinstance(defaultSortField, six.string_types):
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

    def getParamJson(self, name, params, default=None):
        """
        Bound wrapper for :func:`girder.api.rest.getParamJson`.
        """
        return getParamJson(name, params, default)

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
        """
        Helper method to send the authentication cookie
        """
        days = float(self.model('setting').get(SettingKey.COOKIE_LIFETIME))
        token = self.model('token').createToken(user, days=days, scope=scope)

        cookie = cherrypy.response.cookie
        cookie['girderToken'] = str(token['_id'])
        cookie['girderToken']['path'] = '/'
        cookie['girderToken']['expires'] = int(days * 3600 * 24)

        return token

    def deleteAuthTokenCookie(self):
        """
        Helper method to kill the authentication cookie
        """
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

        setResponseHeader('Access-Control-Allow-Methods', allowMethods)
        setResponseHeader('Access-Control-Allow-Headers', allowHeaders)

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


class boundHandler(object):  # noqa: class name
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

        if ctx is None or isinstance(ctx, Resource):  # Used with arguments
            self.ctx = ctx or _sharedContext
            self.func = None

        elif callable(ctx):  # Used as a raw decorator
            self.ctx = _sharedContext
            self.func = ctx
        else:
            raise Exception('ctx in boundhandler must be an instance of '
                            'Resource or a function to be wrapped')

    def __call__(self, *args, **kwargs):
        if self.func is not None:  # Used as a raw decorator
            return self.func(self.ctx, *args, **kwargs)

        else:  # Used with arguments
            fn = args[0]

            @six.wraps(fn)
            def wrapped(*fargs, **fkwargs):
                return fn(self.ctx, *fargs, **fkwargs)
            return wrapped
