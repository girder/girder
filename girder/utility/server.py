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
import functools
import mako
import mimetypes
import os
import posixpath
import six

import girder.events
from girder import constants, logprint, __version__, logStdoutStderr
from girder.utility import plugin_utilities, model_importer, config
from . import webroot

with open(os.path.join(os.path.dirname(__file__), 'error.mako')) as f:
    _errorTemplate = f.read()


def _errorDefault(status, message, *args, **kwargs):
    """
    This is used to render error pages outside of the normal Girder app, such as
    404's. This overrides the default cherrypy error pages.
    """
    return mako.template.Template(_errorTemplate).render(status=status, message=message)


def _configureStaticRoutes(webroot, plugins, event=None):
    """
    Configures static routes for a given webroot.

    This function is also run when the route table setting is modified
    to allow for dynamically changing static routes at runtime.
    """
    # This was triggered by some unrelated setting changing
    if event is not None and event.info['key'] != constants.SettingKey.ROUTE_TABLE:
        return

    routeTable = loadRouteTable()

    # If the static route is a URL, leave it alone
    if '://' in routeTable[constants.GIRDER_STATIC_ROUTE_ID]:
        apiStaticRoot = routeTable[constants.GIRDER_STATIC_ROUTE_ID]
        staticRoot = routeTable[constants.GIRDER_STATIC_ROUTE_ID]
    else:
        # Make the staticRoot relative to the api_root, if possible.  The api_root
        # could be relative or absolute, but it needs to be in an absolute form for
        # relpath to behave as expected.  We always expect the api_root to
        # contain at least two components, but the reference from static needs to
        # be from only the first component.
        apiRootBase = posixpath.split(posixpath.join('/',
                                                     config.getConfig()['server']['api_root']))[0]
        apiStaticRoot = posixpath.relpath(routeTable[constants.GIRDER_STATIC_ROUTE_ID],
                                          apiRootBase)
        staticRoot = posixpath.relpath(routeTable[constants.GIRDER_STATIC_ROUTE_ID],
                                       routeTable[constants.GIRDER_ROUTE_ID])

    webroot.updateHtmlVars({
        'apiRoot': config.getConfig()['server']['api_root'],
        'staticRoot': staticRoot,
        'plugins': plugins
    })

    webroot.api.v1.updateHtmlVars({
        'apiRoot': config.getConfig()['server']['api_root'],
        'staticRoot': apiStaticRoot
    })


def configureServer(test=False, plugins=None, curConfig=None):
    """
    Function to setup the cherrypy server. It configures it, but does
    not actually start it.

    :param test: Set to True when running in the tests.
    :type test: bool
    :param plugins: If you wish to start the server with a custom set of
                    plugins, pass this as a list of plugins to load. Otherwise,
                    will use the PLUGINS_ENABLED setting value from the db.
    :param curConfig: The configuration dictionary to update.
    """
    if curConfig is None:
        curConfig = config.getConfig()

    appconf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'request.show_tracebacks': test,
            'request.methods_with_bodies': ('POST', 'PUT', 'PATCH'),
            'response.headers.server': 'Girder %s' % __version__,
            'error_page.default': _errorDefault
        }
    }
    # Add MIME types for serving Fontello files from staticdir;
    # these may be missing or incorrect in the OS
    mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
    mimetypes.add_type('application/x-font-ttf', '.ttf')
    mimetypes.add_type('application/font-woff', '.woff')

    if test:
        appconf['/src'] = {
            'tools.staticdir.on': True,
            'tools.staticdir.root': constants.STATIC_ROOT_DIR,
            'tools.staticdir.dir': 'clients/web/src',
        }
        appconf['/test'] = {
            'tools.staticdir.on': True,
            'tools.staticdir.root': constants.STATIC_ROOT_DIR,
            'tools.staticdir.dir': 'clients/web/test',
        }
        appconf['/clients'] = {
            'tools.staticdir.on': True,
            'tools.staticdir.root': constants.STATIC_ROOT_DIR,
            'tools.staticdir.dir': 'clients'
        }
        appconf['/plugins'] = {
            'tools.staticdir.on': True,
            'tools.staticdir.root': constants.STATIC_ROOT_DIR,
            'tools.staticdir.dir': 'plugins',
        }

    curConfig.update(appconf)

    if test:
        # Force some config params in testing mode
        curConfig.update({'server': {
            'mode': 'testing',
            'api_root': 'api/v1',
            'static_root': 'static',
            'api_static_root': '../static',
            'cherrypy_server': True
        }})

    mode = curConfig['server']['mode'].lower()
    logprint.info('Running in mode: ' + mode)
    cherrypy.config['engine.autoreload.on'] = mode == 'development'

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api import api_main

    root = webroot.Webroot()
    api_main.addApiToNode(root)

    cherrypy.engine.subscribe('start', girder.events.daemon.start)
    cherrypy.engine.subscribe('stop', girder.events.daemon.stop)

    if plugins is None:
        settings = model_importer.ModelImporter().model('setting')
        plugins = settings.get(constants.SettingKey.PLUGINS_ENABLED, default=())

    _configureStaticRoutes(root, plugins)

    girder.events.bind('model.setting.save.after', '_updateStaticRoutesIfModified',
                       functools.partial(_configureStaticRoutes, root, plugins))

    plugin_utilities.loadPlugins(plugins, root, appconf, root.api.v1)

    return root, appconf


def loadRouteTable(reconcileRoutes=False):
    """
    Retrieves the route table from Girder and reconciles the state of it with the current
    application state.

    Reconciliation ensures that every enabled plugin has a route by assigning default routes for
    plugins that have none, such as newly-enabled plugins.

    :returns: The non empty routes (as a dict of name -> route) to be mounted by CherryPy
              during Girder's setup phase.
    """
    pluginWebroots = {}  # plugin_utilities.getPluginWebroots()
    setting = model_importer.ModelImporter().model('setting')
    routeTable = setting.get(constants.SettingKey.ROUTE_TABLE)

    def reconcileRouteTable(routeTable):
        hasChanged = False

        for name in pluginWebroots.keys():
            if name not in routeTable:
                routeTable[name] = os.path.join('/', name)
                hasChanged = True

        if hasChanged:
            setting.set(constants.SettingKey.ROUTE_TABLE, routeTable)

        return routeTable

    if reconcileRoutes:
        routeTable = reconcileRouteTable(routeTable)

    return {name: route for (name, route) in six.viewitems(routeTable) if route}


def setup(test=False, plugins=None, curConfig=None):
    """
    Configure and mount the Girder server and plugins under the
    appropriate routes.

    See ROUTE_TABLE setting.

    :param test: Whether to start in test mode.
    :param plugins: List of plugins to enable.
    :param curConfig: The config object to update.
    """
    logStdoutStderr()

    pluginWebroots = {}  # plugin_utilities.getPluginWebroots()
    girderWebroot, appconf = configureServer(test, plugins, curConfig)
    routeTable = loadRouteTable(reconcileRoutes=True)

    # Mount Girder
    application = cherrypy.tree.mount(girderWebroot,
                                      str(routeTable[constants.GIRDER_ROUTE_ID]), appconf)

    # Mount static files
    cherrypy.tree.mount(None, routeTable[constants.GIRDER_STATIC_ROUTE_ID],
                        {'/':
                         {'tools.staticdir.on': True,
                          'tools.staticdir.dir': constants.STATIC_ROOT_DIR,
                          'request.show_tracebacks': appconf['/']['request.show_tracebacks'],
                          'response.headers.server': 'Girder %s' % __version__,
                          'error_page.default': _errorDefault}})

    # Mount API (special case)
    # The API is always mounted at /api AND at api relative to the Girder root
    cherrypy.tree.mount(girderWebroot.api, '/api', appconf)

    # Mount everything else in the routeTable
    for (name, route) in six.viewitems(routeTable):
        if name != constants.GIRDER_ROUTE_ID and name in pluginWebroots:
            cherrypy.tree.mount(pluginWebroots[name], route, appconf)

    if test:
        application.merge({'server': {'mode': 'testing'}})

    return application


class _StaticFileRoute(object):
    exposed = True

    def __init__(self, path, contentType=None):
        self.path = os.path.abspath(path)
        self.contentType = contentType

    def GET(self):
        return cherrypy.lib.static.serve_file(self.path,
                                              content_type=self.contentType)


def staticFile(path, contentType=None):
    """
    Helper function to serve a static file. This should be bound as the route
    object, i.e. info['serverRoot'].route_name = staticFile('...')

    :param path: The path of the static file to serve from this route.
    :type path: str
    :param contentType: The MIME type of the static file. If set to None, the
                        content type wll be guessed by the file extension of
                        the 'path' argument.
    """
    return _StaticFileRoute(path, contentType)
