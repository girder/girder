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

import os
import six

from girder import constants
from girder.constants import TerminalColor
from girder.utility import config
from girder.utility.webroot import WebrootBase
from . import docs, access
from .rest import Resource, getApiUrl, getUrlParts

"""
Whenever we add new return values or new options we should increment the
maintenance value. Whenever we add new endpoints, we should increment the minor
version. If we break backward compatibility in any way, we should increment the
major version.  This value is derived from the version number given in
the top level package.json.
"""
API_VERSION = constants.VERSION['apiVersion']

SWAGGER_VERSION = '2.0'


class Description(object):
    """
    This class provides convenient chainable semantics to allow api route
    handlers to describe themselves to the documentation. A route handler
    function can apply the :py:class:`girder.api.describe.describeRoute`
    decorator to itself (called with an instance of this class) in order to
    describe itself.
    """

    # Data Type map from common name or type to (type, format)
    # See Data Type spec:
    #   https://github.com/OAI/OpenAPI-Specification/blob/
    #   0122c22e7fb93b571740dd3c6e141c65563a18be/versions/2.0.md#data-types
    _dataTypeMap = {
        # Primitives
        'integer': ('integer', 'int32'),
        'long': ('integer', 'int64'),
        'number': ('number', None),
        'float': ('number', 'float'),
        'double': ('number', 'double'),
        'string': ('string', None),
        'byte': ('string', 'byte'),
        'binary': ('string', 'binary'),
        'boolean': ('boolean', None),
        'date': ('string', 'date'),
        'dateTime': ('string', 'date-time'),
        'password': ('string', 'password'),
        'file': ('file', None)
    }

    def __init__(self, summary):
        self._summary = summary
        self._params = []
        self._responses = {}
        self._consumes = []
        self._responseClass = None
        self._responseClassArray = False
        self._notes = None

    def asDict(self):
        """
        Returns this description object as an appropriately formatted dict
        """

        # Responses Object spec:
        # The Responses Object MUST contain at least one response code, and it
        # SHOULD be the response for a successful operation call.
        if '200' not in self._responses:
            self._responses['200'] = {
                'description': 'Success'
            }
        if self._responseClass is not None:
            schema = {
                '$ref': '#/definitions/%s' % self._responseClass
            }
            if self._responseClassArray:
                schema = {
                    'type': 'array',
                    'items': schema
                }
            self._responses['200']['schema'] = schema

        resp = {
            'summary': self._summary,
            'responses': self._responses
        }

        if self._params:
            resp['parameters'] = self._params

        if self._notes is not None:
            resp['description'] = self._notes

        if self._consumes:
            resp['consumes'] = self._consumes

        return resp

    def responseClass(self, obj, array=False):
        self._responseClass = obj
        self._responseClassArray = array
        return self

    def param(self, name, description, paramType='query', dataType='string',
              required=True, enum=None, default=None):
        """
        This helper will build a parameter declaration for you. It has the most
        common options as defaults, so you won't have to repeat yourself as much
        when declaring the APIs.

        Note that we could expose more parameters from the Parameter Object
        spec, for example: format, allowEmptyValue, minimum, maximum, pattern,
        uniqueItems.

        :param name: name of the parameter used in the REST query.
        :param description: explanation of the parameter.
        :param paramType: how is the parameter sent.  One of 'query', 'path',
                          'body', 'header', or 'formData'.
        :param dataType: the data type expected in the parameter. This is one
                         of 'integer', 'long', 'float', 'double', 'string',
                         'byte', 'binary', 'boolean', 'date', 'dateTime',
                         'password', or 'file'.
        :param required: True if the request will fail if this parameter is not
                         present, False if the parameter is optional.
        :param enum: a fixed list of possible values for the field.
        """
        # Legacy data type conversions
        if dataType == 'int':
            dataType = 'integer'
        elif dataType == 'File':
            print(TerminalColor.warning(
                "WARNING: dataType 'File' should be updated to 'file'"))
            dataType = 'file'

        # Get type and format from common name
        dataTypeFormat = None
        if dataType in self._dataTypeMap:
            (dataType, dataTypeFormat) = self._dataTypeMap[dataType]
        else:
            print(TerminalColor.warning(
                "WARNING: Invalid dataType '%s' specified for parameter "
                "named '%s'" % (dataType, name)))

        # Parameter Object spec:
        # Since the parameter is not located at the request body, it is limited
        # to simple types (that is, not an object).
        if paramType != 'body':
            if dataType not in ('string', 'number', 'integer', 'boolean',
                                'array', 'file'):
                print(TerminalColor.warning(
                    "WARNING: Invalid dataType '%s' specified for parameter "
                    "named '%s'" % (dataType, name)))

        if paramType == 'form':
            print(TerminalColor.warning(
                "WARNING: paramType 'form' should be updated to 'formData'"))
            paramType = 'formData'

        # Parameter Object spec:
        # If type is "file", then consumes MUST be either
        # "multipart/form-data", "application/x-www-form-urlencoded" or both
        # and the parameter MUST be in "formData".
        if dataType == 'file':
            if paramType != 'formData':
                print(TerminalColor.warning(
                    "WARNING: Invalid paramType '%s' specified for dataType "
                    "'file' in parameter named '%s'"
                    % (paramType, name)))
                paramType = 'formData'

        param = {
            'name': name,
            'description': description,
            'in': paramType,
            'required': required
        }

        if paramType == 'body':
            param['schema'] = {
                'type': dataType
            }
        else:
            param['type'] = dataType

        if dataTypeFormat is not None:
            param['format'] = dataTypeFormat

        if enum:
            param['enum'] = enum

        if default is not None:
            param['default'] = default

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

        if defaultSort is not None:
            self.param('sort', 'Field to sort the result set by.',
                       default=defaultSort, required=False)
            self.param(
                'sortdir', 'Sort order: 1 for ascending, -1 for descending.',
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

        :param reason: The reason or list of reasons why the error occurred.
        :type reason: str, list, or tuple
        :param code: HTTP status code.
        :type code: int
        """
        code = str(code)

        # Combine list of reasons into a single string.
        # swagger-ui renders the description using Markdown.
        if not isinstance(reason, six.string_types):
            reason = '\n\n'.join(reason)

        if code in self._responses:
            print(TerminalColor.warning(
                "WARNING: Error response for code '%s' is already defined "
                "(old: '%s', new: '%s')"
                % (code, self._responses[code]['description'], reason)))

        self._responses[code] = {
            'description': reason
        }

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

        curConfig = config.getConfig()
        mode = curConfig['server'].get('mode', '')

        self.vars = {
            'apiRoot': '',
            'staticRoot': '',
            'title': 'Girder - REST API Documentation',
            'mode': mode
        }


class Describe(Resource):
    def __init__(self):
        super(Describe, self).__init__()
        self.route('GET', (), self.listResources, nodoc=True)

    @access.public
    def listResources(self, params):
        # Paths Object
        paths = {}

        # Definitions Object
        definitions = dict(**docs.models[None])

        # List of Tag Objects
        tags = []

        for resource in sorted(six.viewkeys(docs.routes)):
            # Update Definitions Object
            if resource in docs.models:
                for name, model in six.viewitems(docs.models[resource]):
                    definitions[name] = model

            # Tag Object
            tags.append({
                'name': resource
            })

            for route, methods in six.viewitems(docs.routes[resource]):
                # Path Item Object
                pathItem = {}
                for method, operation in six.viewitems(methods):
                    # Operation Object
                    pathItem[method.lower()] = operation

                paths[route] = pathItem

        apiUrl = getApiUrl()
        urlParts = getUrlParts(apiUrl)
        host = urlParts.netloc
        basePath = urlParts.path

        return {
            'swagger': SWAGGER_VERSION,
            'info': {
                'title': 'Girder REST API',
                'version': API_VERSION
            },
            'host': host,
            'basePath': basePath,
            'tags': tags,
            'paths': paths,
            'definitions': definitions
        }


class describeRoute(object):  # noqa: class name
    def __init__(self, description):
        """
        This returns a decorator to set the API documentation on a route
        handler. Pass the Description object (or None) that you want to use to
        describe this route. It should be used like the following example:

            @describeRoute(
                Description('Do something')
               .param('foo', 'Some parameter', ...)
            )
            def routeHandler(...)

        :param description: The description for the route.
        :type description: :py:class:`girder.api.describe.Description` or None
        """
        self.description = description

    def __call__(self, fun):
        fun.description = self.description
        return fun
