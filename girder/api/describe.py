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

import functools
import os
import six

from girder import constants
from girder.utility.webroot import WebrootBase
from . import docs, access
from .rest import Resource, RestException, getApiUrl

"""
Whenever we add new return values or new options we should increment the
maintenance value. Whenever we add new endpoints, we should increment the minor
version. If we break backward compatibility in any way, we should increment the
major version.  This value is derived from the version number given in
the top level package.json.
"""
API_VERSION = constants.VERSION['apiVersion']

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

        if self._consumes:
            resp['consumes'] = self._consumes

        return resp

    def responseClass(self, obj):
        self._responseClass = obj
        return self

    def param(self, name, description, paramType='query', dataType='string',
              required=True, enum=None, default=None):
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
        if dataType == 'int':
            dataType = 'integer'

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

        if default is not None:
            if dataType == 'boolean':
                param['defaultValue'] = 'true' if default else 'false'
            elif dataType == 'integer' and default == 0:
                param['defaultValue'] = '0'  # workaround swagger-ui bug
            else:
                param['defaultValue'] = default

        self._params.append(param)
        return self

    def pagingParams(self, defaultSort, defaultSortDir=1, defaultLimit=50):
        """
        Adds the limit, offset, sort, and sortdir parameter documentation to
        this route handler.

        :param defaultSort: The default field used to sort the result set.
        :type defaultSort: str
        :param defaultSortDir: Sort order: -1 or 1 (desc or asc)
        :type defaultSortDir: int
        :param defaultLimit: The default page size.
        :type defaultLimit: int
        """
        self.param('limit', 'Result set size limit.', default=defaultLimit,
                   required=False, dataType='int')
        self.param('offset', 'Offset into result set.', default=0,
                   required=False, dataType='int')
        self.param('sort', 'Field to sort the result set by.',
                   default=defaultSort, required=False)
        self.param('sortdir', 'Sort order: 1 for ascending, -1 for descending.',
                   required=False, dataType='int', enum=(1, -1),
                   default=defaultSortDir)
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


class ApiDocs(WebrootBase):
    """
    This serves up the Swagger page.
    """
    def __init__(self, templatePath=None):
        if not templatePath:
            templatePath = os.path.join(constants.PACKAGE_DIR,
                                        'api', 'api_docs.mako')
        super(ApiDocs, self).__init__(templatePath)

        self.vars = {
            'apiRoot': '',
            'staticRoot': '',
            'title': 'Girder - REST API Documentation'
        }


def _cmp(a, b):
    # Since cmp was removed in py3, we use this polyfill instead
    return (a > b) - (a < b)


class Describe(Resource):
    def __init__(self):
        self.route('GET', (), self.listResources, nodoc=True)
        self.route('GET', (':resource',), self.describeResource, nodoc=True)

    @access.public
    def listResources(self, params):
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'apis': [{'path': '/{}'.format(resource)}
                     for resource in sorted(six.viewkeys(docs.routes))]
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
        return _cmp(routeOp1[0].replace('{', ' '),
                    routeOp2[0].replace('{', ' '))

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
            return _cmp(methodOrder.index(method1), methodOrder.index(method2))
        if method1 in methodOrder or method2 in methodOrder:
            return _cmp(method1 not in methodOrder, method2 not in methodOrder)
        return _cmp(method1, method2)

    @access.public
    def describeResource(self, resource, params):
        if resource not in docs.routes:
            raise RestException('Invalid resource: {}'.format(resource))
        return {
            'apiVersion': API_VERSION,
            'swaggerVersion': SWAGGER_VERSION,
            'basePath': getApiUrl(),
            'models': dict(docs.models[resource], **docs.models[None]),
            'apis': [{
                'path': route,
                'operations': sorted(
                    op, key=functools.cmp_to_key(self._compareOperations))
                } for route, op in sorted(
                    six.viewitems(docs.routes[resource]),
                    key=functools.cmp_to_key(self._compareRoutes))
            ]
        }
