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

from girder import constants


class WebrootBase(object):
    """
    Serves a template file in response to GET requests.

    This will typically be the base class of any non-API endpoints.
    """
    exposed = True

    def __init__(self, templatePath):
        with open(templatePath) as templateFile:
            # This may raise an IOError, but there's no way to recover
            self.template = templateFile.read()

        # Rendering occurs lazily on the first GET request
        self.indexHtml = None

        self.vars = {}

    def updateHtmlVars(self, vars):
        """
        If any of the variables in the index html need to change, call this
        with the updated set of variables to render the template with.
        """
        self.vars.update(vars)
        self.indexHtml = None

    def _renderHTML(self):
        return mako.template.Template(self.template).render(**self.vars)

    def GET(self, **params):
        if self.indexHtml is None:
            self.indexHtml = self._renderHTML()

        return self.indexHtml

    def DELETE(self, **params):
        raise cherrypy.HTTPError(405)

    def PATCH(self, **params):
        raise cherrypy.HTTPError(405)

    def POST(self, **params):
        raise cherrypy.HTTPError(405)

    def PUT(self, **params):
        raise cherrypy.HTTPError(405)


class Webroot(WebrootBase):
    """
    The webroot endpoint simply serves the main index HTML file.
    """
    def __init__(self, templatePath=None):
        if not templatePath:
            templatePath = os.path.join(constants.PACKAGE_DIR,
                                        'utility', 'webroot.mako')
        super(Webroot, self).__init__(templatePath)

        self.vars = {
            'plugins': [],
            'apiRoot': '',
            'staticRoot': '',
            'title': 'Girder'
        }

    def _renderHTML(self):
        self.vars['pluginCss'] = []
        self.vars['pluginJs'] = []
        builtDir = os.path.join(constants.STATIC_ROOT_DIR, 'clients', 'web',
                                'static', 'built', 'plugins')
        for plugin in self.vars['plugins']:
            if os.path.exists(os.path.join(builtDir, plugin, 'plugin.min.css')):
                self.vars['pluginCss'].append(plugin)
            if os.path.exists(os.path.join(builtDir, plugin, 'plugin.min.js')):
                self.vars['pluginJs'].append(plugin)

        return super(Webroot, self)._renderHTML()
