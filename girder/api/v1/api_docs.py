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
import os

from girder.constants import ROOT_DIR

from ..rest import Resource, RestException

"""
Whenever we add new return values or new options we should increment the
maintenance value. Whenever we add new endpoints, we should increment the minor
version. If we break backward compatibility in any way, we should increment the
major version.
"""
API_VERSION = "1.0.0"


class ApiDocs(object):
    exposed = True

    def GET(self, **params):
        return cherrypy.lib.static.serve_file(os.path.join(
            ROOT_DIR, 'clients', 'web', 'static', 'built', 'swagger',
            'swagger.html'), content_type='text/html')


class Describe(Resource):
    discovery = {
        'apis': []
        }
    resources = {}
    models = {}

    @classmethod
    def param(cls, name, description, paramType='query', dataType='string',
              required=True):
        """
        This helper will build a parameter declaration for you. It has the most
        common options as defaults, so you won't have to repeat yourself as much
        when declaring the APIs.
        """
        return {
            'name': name,
            'description': description,
            'paramType': paramType,
            'dataType': dataType,
            'allowMultiple': False,
            'required': required
            }

    @classmethod
    def errorResponse(cls, reason='A parameter was invalid.', code=400):
        """
        This helper will build an errorResponse declaration for you. Most
        endpoints will be able to use the default parameter values for one of
        their responses.
        """
        return {
            'reason': reason,
            'code': code
            }

    @classmethod
    def declareApi(cls, resource, apis):
        """
        Rest modules should call this to document themselves. The specification
        can be found at:
        https://github.com/wordnik/swagger-core/wiki/API-Declaration.
        :param resource: The name of the resource, e.g. 'user'
        :type resource: str
        :param apis: The object(s) to add to the list for this resource.
        :type apis: list or dict
        """
        cls.discovery['apis'].append({
            'path': '/%s' % resource
            })

        if type(apis) is list:
            cls.resources[resource] = apis
        else:
            cls.resources[resource] = [apis]

    @Resource.endpoint
    def GET(self, path, params):
        """
        Outputs the API description as a swagger-compliant JSON document.
        """
        retVal = {}
        if path:
            resources = self.__class__.resources
            if path[0] in resources:
                retVal['apis'] = resources[path[0]]
            else:
                raise RestException('Invalid resource name "%s"' % path[0])
            retVal['basePath'] = os.path.dirname(
                os.path.dirname(cherrypy.url()))
        else:
            retVal['basePath'] = cherrypy.url()
            retVal['apis'] = self.__class__.discovery['apis']

        retVal['apiVersion'] = API_VERSION
        retVal['swaggerVersion'] = '1.1'

        return retVal
