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

import json
import os
import re

import cherrypy
import mako

from girder import constants
from girder.constants import SettingKey
from girder.models.setting import Setting
from girder.utility import config


class WebrootBase(object):
    """
    Serves a template file in response to GET requests.

    This will typically be the base class of any non-API endpoints.
    """
    exposed = True

    def __init__(self, templatePath):
        self.vars = {}
        self.config = config.getConfig()

        self._templateDirs = []
        self.setTemplatePath(templatePath)

    def updateHtmlVars(self, vars):
        """
        If any of the variables in the index html need to change, call this
        with the updated set of variables to render the template with.
        """
        self.vars.update(vars)

    def setTemplatePath(self, templatePath):
        """
        Set the path to a template file to render instead of the default template.

        The default template remains available so that custom templates can
        inherit from it. To do so, save the default template filename from
        the templateFilename attribute before calling this function, pass
        it as a variable to the custom template using updateHtmlVars(), and
        reference that variable in an <%inherit> directive like:

            <%inherit file="${context.get('defaultTemplateFilename')}"/>
        """
        templateDir, templateFilename = os.path.split(templatePath)
        self._templateDirs.append(templateDir)
        self.templateFilename = templateFilename

        # Reset TemplateLookup instance so that it will be instantiated lazily,
        # with the latest template directories, on the next GET request
        self._templateLookup = None

    @staticmethod
    def _escapeJavascript(string):
        # Per the advice at:
        # https://www.owasp.org/index.php/XSS_(Cross_Site_Scripting)_Prevention_Cheat_Sheet#Output_Encoding_Rules_Summary
        # replace all non-alphanumeric characters with "\0uXXXX" unicode escaping:
        # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar#Unicode_escape_sequences
        return re.sub(
            r'[^a-zA-Z0-9]',
            lambda match: '\\u%04X' % ord(match.group()),
            string
        )

    def _renderHTML(self):
        if self._templateLookup is None:
            self._templateLookup = mako.lookup.TemplateLookup(directories=self._templateDirs)

        template = self._templateLookup.get_template(self.templateFilename)
        return template.render(js=self._escapeJavascript, json=json.dumps, **self.vars)

    def GET(self, **params):
        return self._renderHTML()

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
            templatePath = os.path.join(constants.PACKAGE_DIR, 'utility', 'webroot.mako')
        super(Webroot, self).__init__(templatePath)

        self.vars = {
            # 'title' is deprecated use brandName instead
            'title': 'Girder'
        }

    def _renderHTML(self):
        from girder.utility import server
        from girder.plugin import loadedPlugins
        self.vars['plugins'] = loadedPlugins()
        self.vars['pluginCss'] = []
        self.vars['pluginJs'] = []
        builtDir = os.path.join(constants.STATIC_ROOT_DIR, 'built', 'plugins')
        for plugin in self.vars['plugins']:
            if os.path.exists(os.path.join(builtDir, plugin, 'plugin.min.css')):
                self.vars['pluginCss'].append(plugin)
            if os.path.exists(os.path.join(builtDir, plugin, 'plugin.min.js')):
                self.vars['pluginJs'].append(plugin)

        self.vars['apiRoot'] = server.getApiRoot()
        self.vars['staticRoot'] = server.getStaticRoot()
        self.vars['brandName'] = Setting().get(SettingKey.BRAND_NAME)
        self.vars['contactEmail'] = Setting().get(
            SettingKey.CONTACT_EMAIL_ADDRESS)
        self.vars['privacyNoticeHref'] = Setting().get(SettingKey.PRIVACY_NOTICE)
        self.vars['bannerColor'] = Setting().get(SettingKey.BANNER_COLOR)
        self.vars['registrationPolicy'] = Setting().get(SettingKey.REGISTRATION_POLICY)
        self.vars['enablePasswordLogin'] = Setting().get(SettingKey.ENABLE_PASSWORD_LOGIN)

        return super(Webroot, self)._renderHTML()
