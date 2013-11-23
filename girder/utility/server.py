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

import os
import cherrypy

from girder.constants import ROOT_DIR


class Webroot(object):
    """
    The webroot endpoint simply serves the main index.html file.
    """
    exposed = True

    def GET(self):
        return cherrypy.lib.static.serve_file(
            os.path.join(ROOT_DIR, 'clients', 'web', 'static', 'built',
                         'index.html'), content_type='text/html')


def setup(test=False):
    """
    Function to setup the cherrypy server. It configures it, but does
    not actually start it.

    :param test: Set to True when running in the tests.
    :type test: bool
    """
    cfgs = ['auth', 'db', 'server']
    cfgs = [os.path.join(ROOT_DIR, 'girder', 'conf', 'local.%s.cfg' % c)
            for c in cfgs]
    [cherrypy.config.update(cfg) for cfg in cfgs]

    appconf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.staticdir.root': ROOT_DIR,
            'request.show_tracebacks': test
            },
        '/static': {
            'tools.staticdir.on': 'True',
            'tools.staticdir.dir': 'clients/web/static',
            }
        }

    cherrypy.config.update(appconf)

    if test:
        # Force the mode to be 'testing'
        cherrypy.config.update({'server': {'mode': 'testing'}})

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api import api_main

    root = Webroot()
    root = api_main.addApiToNode(root)

    application = cherrypy.tree.mount(root, '/', appconf)
    [application.merge(cfg) for cfg in cfgs]

    if test:
        application.merge({'server': {'mode': 'testing'}})
