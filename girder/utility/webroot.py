import json
import os
import re

import cherrypy
import mako

from girder.utility import config


class WebrootBase:
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
