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
import os

from girder.constants import ROOT_DIR
from . import describe
from .rest import Resource, RestException, endpoint

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

    @classmethod
    def addRouteDocs(cls, resource, apis):
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
            'path': '/{}'.format(resource)
        })

        if type(apis) is list:
            cls.resources[resource] = apis
        else:
            cls.resources[resource] = [apis]

    @endpoint
    def GET(self, path, params):
        """
        Outputs the API description as a swagger-compliant JSON document.
        """
        retVal = {}
        if path:
            if path[0] in describe.routes:
                retVal['apis'] = [{'path': route, 'operations': methods}
                                  for route, methods
                                  in describe.routes[path[0]].iteritems()]
            else:
                raise RestException('Invalid resource: {}'.format(path[0]))
            retVal['basePath'] = os.path.dirname(
                os.path.dirname(cherrypy.url()))
        else:
            retVal['basePath'] = cherrypy.url()
            retVal['apis'] = [{'path': '/{}'.format(resource)}
                              for resource in describe.discovery]

        retVal['apiVersion'] = API_VERSION
        retVal['swaggerVersion'] = '1.2'

        return retVal
