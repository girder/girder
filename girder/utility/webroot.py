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

import mako
import os

from girder import constants


class Webroot(object):
    """
    The webroot endpoint simply serves the main index HTML file.
    """
    exposed = True

    indexHtml = None

    vars = {
        'plugins': [],
        'apiRoot': '',
        'staticRoot': '',
        'title': 'Girder'
    }

    def __init__(self, templatePath=None):
        if not templatePath:
            templatePath = os.path.join(constants.PACKAGE_DIR,
                                        'utility', 'webroot.mako')
        with open(templatePath) as templateFile:
            # This may raise an IOError, but there's no way to recover
            self.template = templateFile.read()

    def GET(self):
        if self.indexHtml is None:
            self.vars['pluginCss'] = []
            self.vars['pluginJs'] = []
            builtDir = os.path.join(constants.STATIC_ROOT_DIR, 'clients',
                                    'web', 'static', 'built', 'plugins')
            for plugin in self.vars['plugins']:
                if os.path.exists(os.path.join(builtDir, plugin,
                                               'plugin.min.css')):
                    self.vars['pluginCss'].append(plugin)
                if os.path.exists(os.path.join(builtDir, plugin,
                                               'plugin.min.js')):
                    self.vars['pluginJs'].append(plugin)

            self.indexHtml = mako.template.Template(self.template).render(
                **self.vars)

        return self.indexHtml

    def updateHtmlVars(self, vars):
        """
        If any of the variables in the index html need to change, call this
        with the updated set of variables to render the template with.
        """
        self.vars.update(vars)
        self.indexHtml = None
