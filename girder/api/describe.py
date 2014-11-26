#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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
import mako
import os

from girder.constants import VERSION
from . import docs, access
from .rest import Resource, RestException

"""
Whenever we add new return values or new options we should increment the
maintenance value. Whenever we add new endpoints, we should increment the minor
version. If we break backward compatibility in any way, we should increment the
major version.  This value is derived from the version number given in
the top level package.json.
"""
API_VERSION = VERSION['apiVersion']

SWAGGER_VERSION = '1.2'


class Description(object):
    """
    This class provides convenient chainable semantics to allow api route
    handlers to describe themselves to the documentation. A route handler
    function can set a description property on itself to an instance of this
    class in order to describe itself.
    """
    def __init__(self, summary):
        self._summary = summary
        self._params = []
        self._responses = []
        self._consumes = []
        self._responseClass = None
        self._notes = None

    def asDict(self):
        """
        Returns this description object as an appropriately formatted dict
        """
        resp = {
            'summary': self._summary,
            'notes': self._notes,
            'parameters': self._params,
            'responseMessages': self._responses,
            'responseClass': self._responseClass
        }

        if self._consumes is not None:
            resp['consumes'] = self._consumes

        return resp

    def responseClass(self, obj):
        self._responseClass = obj
        return self

    def param(self, name, description, paramType='query', dataType='string',
              required=True, enum=None):
        """
        This helper will build a parameter declaration for you. It has the most
        common options as defaults, so you won't have to repeat yourself as much
        when declaring the APIs.

        Note that we could expose more parameters: allowMultiple, format,
        defaultValue, minimum, maximum, uniqueItems, $ref, type (return type).
        We also haven't exposed the complex data types.

        :param name: name of the parameter used in the REST query.
        :param description: explanation of the parameter.
        :param paramType: how is the parameter sent.  One of 'query', 'path',
                          'body', 'header', or 'form'.
        :param dataType: the data type expected in the parameter.  This is one
                         of 'integer', 'long', 'float', 'double', 'string',
                         'byte', 'boolean', 'date', 'dateType', 'array', or
                         'File'.
        :param required: True if the request will fail if this parameter is not
                         present, False if the parameter is optional.
        :param enum: a fixed list of possible values for the field.
        """
        param = {
            'name': name,
            'description': description,
            'paramType': paramType,
            'type': dataType,
            'allowMultiple': False,
            'required': required
        }
        if enum:
            param['enum'] = enum
        self._params.append(param)
        return self

    def consumes(self, value):
        self._consumes.append(value)
        return self

    def notes(self, notes):
        self._notes = notes
        return self

    def errorResponse(self, reason='A parameter was invalid.', code=400):
        """
        This helper will build an errorResponse declaration for you. Many
        endpoints will be able to use the default parameter values for one of
        their responses.
        """
        self._responses.append({
            'message': reason,
            'code': code
        })
        return self


class ApiDocs(object):
    """
    This serves up the swagger page.
    """
    exposed = True

    indexHtml = None

    vars = {
        'staticRoot': '',
        'title': 'Girder - REST API Documentation'
    }

    template = r"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <title>${title}</title>
        <link rel="stylesheet"
            href="//fonts.googleapis.com/css?family=Droid+Sans:400,700">
        <link rel="stylesheet"
            href="${staticRoot}/lib/fontello/css/fontello.css">
        <link rel="stylesheet"
            href="${staticRoot}/built/swagger/css/reset.css">
        <link rel="stylesheet"
            href="${staticRoot}/built/swagger/css/screen.css">
        <link rel="stylesheet"
            href="${staticRoot}/built/swagger/docs.css">
        <link rel="icon"
            type="image/png"
            href="${staticRoot}/img/Girder_Favicon.png">
      </head>
      <body>
        <div class="docs-header">
          <span>Girder REST API Documentation</span>
          <i class="icon-book-alt right"></i>
        </div>
        <div class="docs-body">
          <p>Below you will find the list of all of the resource types exposed
          by the Girder RESTful Web API. Click any of the resource links to open
          up a list of all available endpoints related to each resource type.
          </p>
          <p>Clicking any of those endpoints will display detailed documentation
          about the purpose of each endpoint and the input parameters and output
          values. You can also call API endpoints directly from this page by
          typing in the parameters you wish to pass and then clicking the "Try
          it out!" button.</p>
          <p><b>Warning:</b> This is not a sandbox&mdash;calls that you make
          from this page are the same as calling the API with any other client,
          so update or delete calls that you make will affect the actual data on
          the server.</p>
        </div>
        <div class="swagger-section">
          <div id="swagger-ui-container"
              class="swagger-ui-wrap docs-swagger-container">
          </div>
        </div>
        <script src="${staticRoot}/built/swagger/lib/jquery-1.8.0.min.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/jquery.slideto.min.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/jquery.wiggle.min.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/jquery.ba-bbq.min.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/handlebars-1.0.0.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/underscore-min.js">
        </script>
        <script src="${staticRoot}/built/swagger/lib/backbone-min.js"></script>
        <script src="${staticRoot}/built/swagger/lib/shred.bundle.js"></script>
        <script src="${staticRoot}/built/swagger/lib/swagger.js"></script>
        <script src="${staticRoot}/built/swagger/swagger-ui.min.js"></script>
        <script src="${staticRoot}/built/swagger/lib/highlight.7.3.pack.js">
        </script>
        <script src="${staticRoot}/girder-swagger.js"></script>
      </body>
    </html>
    """

    def updateHtmlVars(self, vars):
        self.vars.update(vars)
        self.indexHtml = None

    def GET(self, **params):
        if self.indexHtml is None:
            self.indexHtml = mako.template.Template(self.template).render(
                **self.vars)

        return self.indexHtml

    def DELETE(self, **params):
        raise cherrypy.HTTPError(405)

    def PATCH(self, **params):
        raise cherrypy.HTTPError(405)

    def POST(self, **params):
        raise cherrypy.HTTPError(405)

    def PUT(self, **params):
        raise cherrypy.HTTPError(405)


class Describe(Resource):
    def __init__(self):
        self.route('GET', (), self.listResources, nodoc=True)
        self.route('GET', (':resource',), self.describeResource, nodoc=True)

    @access.public
    def listResources(self, params):
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'basePath': cherrypy.url(),
            'apis': [{'path': '/{}'.format(resource)}
                     for resource in sorted(docs.discovery)]
        }

    def _compareRoutes(self, routeOp1, routeOp2):
        """
        Order routes based on path.  Alphabetize this, treating parameters as
        before fixed paths.
        :param routeOp1: tuple of (route, op) to compare
        :param routeOp2: tuple of (route, op) to compare
        :returns: negative if routeOp1<routeOp2, positive if routeOp1>routeOp2.
        """
        # replacing { with ' ' is a simple way to make ASCII sort do what we
        # want for routes.  We would have to do more work if we allow - in
        # routes
        return cmp(routeOp1[0].replace('{', ' '), routeOp2[0].replace('{', ' '))

    def _compareOperations(self, op1, op2):
        """
        Order operations in our preferred method order.  methods not in our
        list are put afterwards and sorted alphabetically.
        :param op1: first operation dictionary to compare.
        :param op2: second operation dictionary to compare.
        :returns: negative if op1<op2, positive if op1>op2.
        """
        methodOrder = ['GET', 'PUT', 'POST', 'PATCH', 'DELETE']
        method1 = op1.get('httpMethod', '')
        method2 = op2.get('httpMethod', '')
        if method1 in methodOrder and method2 in methodOrder:
            return cmp(methodOrder.index(method1), methodOrder.index(method2))
        if method1 in methodOrder or method2 in methodOrder:
            return cmp(method1 not in methodOrder, method2 not in methodOrder)
        return cmp(method1, method2)

    @access.public
    def describeResource(self, resource, params):
        if resource not in docs.routes:
            raise RestException('Invalid resource: {}'.format(resource))
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'basePath': os.path.dirname(os.path.dirname(cherrypy.url())),
            'models': docs.models,
            'apis': [{'path': route,
                      'operations': sorted(op, self._compareOperations)}
                     for route, op in sorted(docs.routes[resource].iteritems(),
                                             self._compareRoutes)]
        }
