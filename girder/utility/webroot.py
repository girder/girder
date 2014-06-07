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

    template = r"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <title>${title}</title>
        <link rel="stylesheet"
              href="//fonts.googleapis.com/css?family=Droid+Sans:400,700">
        <link rel="stylesheet"
              href="${staticRoot}/lib/bootstrap/css/bootstrap.min.css">
        <link rel="stylesheet"
              href="${staticRoot}/lib/bootstrap/css/bootstrap-switch.min.css">
        <link rel="stylesheet"
              href="${staticRoot}/lib/fontello/css/fontello.css">
        <link rel="stylesheet"
              href="${staticRoot}/lib/fontello/css/animation.css">
        <link rel="stylesheet"
              href="${staticRoot}/lib/jqplot/css/jquery.jqplot.min.css">
        <link rel="stylesheet"
              href="${staticRoot}/built/app.min.css">
        <link rel="icon"
              type="image/png"
              href="${staticRoot}/img/Girder_Favicon.png">

        % for plugin in pluginCss:
            <link rel="stylesheet"
                  href="${staticRoot}/built/plugins/${plugin}/plugin.min.css">
        % endfor
      </head>
      <body>
        <div id="g-global-info-apiroot" class="hide">${apiRoot}</div>
        <div id="g-global-info-staticroot" class="hide">${staticRoot}</div>
        <script src="${staticRoot}/built/libs.min.js"></script>
        <script src="${staticRoot}/built/app.min.js"></script>
        <script src="${staticRoot}/built/main.min.js"></script>

        % for plugin in pluginJs:
          <script src="${staticRoot}/built/plugins/${plugin}/plugin.min.js">
          </script>
        % endfor
      </body>
    </html>
    """

    def GET(self):
        if self.indexHtml is None:
            self.vars['pluginCss'] = []
            self.vars['pluginJs'] = []
            builtDir = os.path.join(constants.ROOT_DIR, 'clients', 'web',
                                    'static', 'built', 'plugins')
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
