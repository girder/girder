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
import pymongo
import sys
import traceback
import types

from . import docs
from girder import events, logger
from girder.constants import AccessType, TerminalColor
from girder.models.model_base import AccessException, ValidationException,\
    AccessControlledModel
from girder.utility.model_importer import ModelImporter
from girder.utility import config
from bson.objectid import ObjectId, InvalidId


_importer = ModelImporter()


def _cacheAuthUser(fun):
    """
    This decorator for getCurrentUser ensures that the authentication procedure
    is only performed once per request, and is cached on the request for
    subsequent calls to getCurrentUser().
    """
    def inner(self, *args, **kwargs):
        if hasattr(cherrypy.request, 'girderUser'):
            return cherrypy.request.girderUser

        user = fun(self, *args, **kwargs)
        if type(user) is tuple:
            setattr(cherrypy.request, 'girderUser', user[0])
        else:
            setattr(cherrypy.request, 'girderUser', user)

        return user
    return inner


def loadmodel(map, model, level=None):
    """
    This is a meta-decorator that can be used to convert parameters that are
    ObjectID's into the actual documents.
    """
    _model = _importer.model(model)

    def meta(fun):
        def wrapper(self, *args, **kwargs):
            for raw, converted in map.iteritems():
                if level is not None:
                    user = self.getCurrentUser()
                    kwargs[converted] = _model.load(
                        id=kwargs[raw], level=level, user=user)
                else:
                    kwargs[converted] = _model.load(kwargs[raw])

                if kwargs[converted] is None:
                    raise RestException('Invalid {} id ({}).'
                                        .format(model, kwargs[raw]))
                del kwargs[raw]
            return fun(self, *args, **kwargs)
        return wrapper
    return meta


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
    def endpointDecorator(self, *args, **kwargs):
        try:
            # First, we should encode any unicode form data down into
            # UTF-8 so the actual REST classes are always dealing with
            # str types.
            params = {}
            for k, v in kwargs.iteritems():
                if type(v) in (str, unicode):
                    params[k] = v.encode('utf-8')
                else:
                    params[k] = v  # pragma: no cover

            val = fun(self, args, params)

            if isinstance(val, types.FunctionType):
                # If the endpoint returned a function, we assume it's a
                # generator function for a streaming response.
                cherrypy.response.stream = True
                return val()

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
            val = {'message': e.message, 'type': 'access'}
        except ValidationException as e:
            cherrypy.response.status = 400
            val = {'message': e.message, 'type': 'validation'}
            if e.field is not None:
                val['field'] = e.field
        except cherrypy.HTTPRedirect:
            raise
        except:  # pragma: no cover
            # These are unexpected failures; send a 500 status
            logger.exception('500 Error')
            cherrypy.response.status = 500
            t, value, tb = sys.exc_info()
            val = {'message': '%s: %s' % (t.__name__, str(value)),
                   'type': 'internal'}
            curConfig = config.getConfig()
            if curConfig['server']['mode'] != 'production':
                # Unless we are in production mode, send a traceback too
                val['trace'] = traceback.extract_tb(tb)

        accepts = cherrypy.request.headers.elements('Accept')
        for accept in accepts:
            if accept.value == 'application/json':
                break
            elif accept.value == 'text/html':  # pragma: no cover
                # Pretty-print and HTMLify the response for the browser
                cherrypy.response.headers['Content-Type'] = 'text/html'
                resp = json.dumps(val, indent=4, sort_keys=True,
                                  separators=(',', ': '), default=str)
                resp = resp.replace(' ', '&nbsp;').replace('\n', '<br />')
                resp = '<div style="font-family:monospace;">%s</div>' % resp
                return resp

        # Default behavior will just be normal JSON output. Keep this
        # outside of the loop body in case no Accept header is passed.
        cherrypy.response.headers['Content-Type'] = 'application/json'
        return json.dumps(val, default=str)
    return endpointDecorator


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
    exposed = True

    def route(self, method, route, handler, nodoc=False, resource=None):
        """
        Define a route for your REST resource.

        :param method: The HTTP method, e.g. 'GET', 'POST', 'PUT'
        :type method: str
        :param route: The route, as a list of path params relative to the
        resource root. Elements of this list starting with ':' are assumed to
        be wildcards.
        :type route: list
        :param handler: The method to be called if the route and method are
        matched by a request. Wildcards in the route will be expanded and
        passed as kwargs with the same name as the wildcard identifier.
        :type handler: function
        :param nodoc: If your route intentionally provides no documentation,
                      set this to True to disable the warning on startup.
        :type nodoc: bool
        """
        if not hasattr(self, '_routes'):
            self._routes = collections.defaultdict(
                lambda: collections.defaultdict(list))

        # Insertion sort to maintain routes in required order.
        def shouldInsert(a, b):
            """
            Return bool representing whether route a should go before b. Checks
            by comparing each token in order and making sure routes with
            literals in forward positions come before routes with wildcards
            in those positions.
            """
            for i in xrange(0, len(a)):
                if a[i][0] != ':' and b[i][0] == ':':
                    return True
            return False

        nLengthRoutes = self._routes[method.lower()][len(route)]
        for i in xrange(0, len(nLengthRoutes)):
            if shouldInsert(route, nLengthRoutes[i][0]):
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
            docs.addRouteDocs(
                resource=resource, route=route, method=method,
                info=handler.description.asDict(), handler=handler)
        elif not nodoc:
            routePath = '/'.join([resource] + list(route))
            print TerminalColor.warning(
                'WARNING: No description docs present for route {} {}'
                .format(method, routePath))

    def handleRoute(self, method, path, params):
        """
        Match the requested path to its corresponding route, and calls the
        handler for that route with the appropriate kwargs. If no route
        matches the path requested, throws a RestException.

        This method fires two events for each request if a matching route is
        found. The names of these events are derived from the route matched by
        the request. As an example, if the user calls GET /api/v1/item/123,
        the following two events would be fired:

            rest.get.item/:id.before

        would be fired prior to calling the default API function, and

            rest.get.item/:id.after

        would be fired after the route handler returns. The query params are
        passed in the info of the before and after event handlers as
        event.info['params'], and the matched route tokens are passed in
        as dict items of event.info, so in the previous example event.info would
        also contain an 'id' key with the value of 123. For endpoints with empty
        sub-routes, the trailing slash is omitted from the event name, e.g.:

            rest.post.group.before

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
        Pass a list of required parameters.
        """
        for param in required:
            if param not in provided:
                raise RestException("Parameter '%s' is required." % param)

    def requireAdmin(self, user):
        """
        Calling this on a user will ensure that they have admin rights.
        an AccessException.

        :param user: The user to check admin flag on.
        :type user: dict.
        :raises AccessException: If the user is not an administrator.
        """

        if user is None or user.get('admin', False) is not True:
            raise AccessException('Administrator access required.')

    def getPagingParameters(self, params, defaultSortField=None):
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
        sortdir = int(params.get('sortdir', pymongo.ASCENDING))

        if 'sort' in params:
            sort = [(params['sort'].strip(), sortdir)]
        elif type(defaultSortField) is str:
            sort = [(defaultSortField, sortdir)]
        else:
            sort = None

        return (limit, offset, sort)

    @_cacheAuthUser
    def getCurrentUser(self, returnToken=False):
        """
        Returns the current user from the long-term cookie token.

        :param returnToken: Whether we should return a tuple that also contains
                            the token.
        :type returnToken: bool
        :returns: The user document from the database, or None if the user
                  is not logged in or the cookie token is invalid or expired.
                  If returnToken=True, returns a tuple of (user, token).
        """
        event = events.trigger('auth.user.get')
        if event.defaultPrevented and len(event.responses) > 0:
            return event.responses[0]

        cookie = cherrypy.request.cookie
        if 'authToken' in cookie:
            info = json.loads(cookie['authToken'].value)
            try:
                userId = ObjectId(info['userId'])
            except:
                return (None, None) if returnToken else None

            user = self.model('user').load(userId, force=True)
            token = self.model('token').load(info['token'], AccessType.ADMIN,
                                             objectId=False, user=user)

            if token is None or token['expires'] < datetime.datetime.now():
                return (None, token) if returnToken else None
            else:
                return (user, token) if returnToken else user
        elif 'token' in cherrypy.request.params:  # Token as a parameter
            token = self.model('token').load(
                cherrypy.request.params.get('token'), objectId=False,
                force=True)
            user = self.model('user').load(token['userId'], force=True)

            if token is None or token['expires'] < datetime.datetime.now():
                return (None, token) if returnToken else None
            else:
                return (user, token) if returnToken else user

        else:  # user is not logged in
            return (None, None) if returnToken else None

    @endpoint
    def DELETE(self, path, params):
        return self.handleRoute('DELETE', path, params)

    @endpoint
    def GET(self, path, params):
        return self.handleRoute('GET', path, params)

    @endpoint
    def POST(self, path, params):
        return self.handleRoute('POST', path, params)

    @endpoint
    def PUT(self, path, params):
        return self.handleRoute('PUT', path, params)
