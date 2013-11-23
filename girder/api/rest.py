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
import json
import pymongo
import sys
import traceback
import types

from girder.constants import AccessType
from girder.models.model_base import AccessException, ValidationException
from girder.utility.model_importer import ModelImporter
from bson.objectid import ObjectId, InvalidId


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

    def __init__(self):
        self.initialize()

    def initialize(self):
        """
        Subclasses should implement this method.
        """
        pass  # pragma: no cover

    def filterDocument(self, doc, allow=[]):
        """
        This method will filter the given document to make it suitable to
        output to the user.

        :param doc: The document to filter.
        :type doc: dict
        :param allow: The whitelist of fields to allow in the output document.
        :type allow: List of strings
        """
        if doc is None:
            return None

        out = {}
        for field in allow:
            if field in doc:
                out[field] = doc[field]

        return out

    def requireParams(self, required, provided):
        """
        Pass a list of required parameters.
        """
        for param in required:
            if not param in provided:
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
        # TODO we should also allow them to pass the token in the params
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
        else:  # user is not logged in
            return (None, None) if returnToken else None

    def getObjectById(self, model, id, checkAccess=False, user=None,
                      level=AccessType.READ, objectId=True):
        """
        This convenience method should be used to load a single
        instance of a model that is indexed by the default ObjectId type.

        :param model: The model to load from.
        :type model: Model
        :param id: The id of the object.
        :type id: string or ObjectId
        :param checkAccess: Whether the object being request is an
                            AccessControlledObject.
        :type checkAccess: bool
        :param user: If checkAccess=True, set this to the current user.
        :type user: dict or None
        :param level: If the model is an AccessControlledModel, you must
                     pass the user requesting access
        """
        try:
            if checkAccess is True:
                obj = model.load(id=id, objectId=objectId, user=user,
                                 level=level)
            else:
                obj = model.load(id=id, objectId=objectId)
        except InvalidId:
            raise RestException('Invalid object ID format.')
        if obj is None:
            raise RestException('Resource not found.')
        return obj

    @classmethod
    def endpoint(cls, fun):
        """
        All REST endpoints should use this decorator. It converts the return
        value of the underlying method to the appropriate output format and
        sets the relevant response headers. It also handles RestExceptions,
        which are 400-level exceptions in the REST endpoints, AccessExceptions
        resulting from access denial, and also handles any unexpected errors
        using 500 status and including a useful traceback in those cases.

        If you want a streamed response, simply return a generator function
        from the inner method.
        """
        def wrapper(self, *args, **kwargs):
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
                    cherrypy.request.config['response.stream'] = True
                    return val()

            except RestException as e:
                # Handle all user-error exceptions from the rest layer
                cherrypy.response.status = e.code
                val = {'message': e.message,
                       'type': 'rest'}
                if e.extra is not None:
                    val['extra'] = e.extra
            except AccessException as e:
                # Handle any permission exceptions
                cherrypy.response.status = 403
                val = {'message': e.message,
                       'type': 'access'}
            except ValidationException as e:
                cherrypy.response.status = 400
                val = {'message': e.message,
                       'type': 'validation'}
                if e.field is not None:
                    val['field'] = e.field
            except:  # pragma: no cover
                # These are unexpected failures; send a 500 status
                cherrypy.response.status = 500
                t, value, tb = sys.exc_info()
                val = {'message': '%s: %s' % (t.__name__, str(value)),
                       'type': 'internal'}
                if cherrypy.config['server']['mode'] != 'production':
                    # Unless we are in production mode, send a traceback too
                    val['trace'] = traceback.extract_tb(tb)[1:]

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
        return wrapper
