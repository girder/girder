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
import mimetypes
import os
import posixpath
import six

import girder.events
from girder import constants, logprint, __version__, logStdoutStderr, _setupCache
from girder.models.setting import Setting
from girder import plugin
from girder.utility import config
from . import webroot

with open(os.path.join(os.path.dirname(__file__), 'error.mako')) as f:
    _errorTemplate = f.read()


def _errorDefault(status, message, *args, **kwargs):
    """
    This is used to render error pages outside of the normal Girder app, such as
    404's. This overrides the default cherrypy error pages.
    """
    return mako.template.Template(_errorTemplate).render(status=status, message=message)


def getPlugins():
    plugins = Setting().get(constants.SettingKey.PLUGINS_ENABLED, default=())
    return plugins


def getApiRoot():
    return config.getConfig()['server']['api_root']


def getStaticRoot():
    routeTable = loadRouteTable()
    return routeTable[constants.GIRDER_STATIC_ROUTE_ID]


def getApiStaticRoot():
    routeTable = loadRouteTable()

    # If the static route is a URL, leave it alone
    if '://' in routeTable[constants.GIRDER_STATIC_ROUTE_ID]:
        return routeTable[constants.GIRDER_STATIC_ROUTE_ID]
    else:
        # Make the staticRoot relative to the api_root, if possible.  The api_root
        # could be relative or absolute, but it needs to be in an absolute form for
        # relpath to behave as expected.  We always expect the api_root to
        # contain at least two components, but the reference from static needs to
        # be from only the first component.
        apiRootBase = posixpath.split(posixpath.join('/',
                                                     config.getConfig()['server']['api_root']))[0]
        return posixpath.relpath(routeTable[constants.GIRDER_STATIC_ROUTE_ID],
                                 apiRootBase)


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

    _setupCache()

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api import api_main

    root = webroot.Webroot()
    api_main.addApiToNode(root)

    girder.events.setupDaemon()
    cherrypy.engine.subscribe('start', girder.events.daemon.start)
    cherrypy.engine.subscribe('stop', girder.events.daemon.stop)

    if plugins is None:
        plugins = getPlugins()

    routeTable = loadRouteTable()
    info = {
        'config': appconf,
        'serverRoot': root,
        'serverRootPath': routeTable[constants.GIRDER_ROUTE_ID],
        'apiRoot': root.api.v1,
        'staticRoot': routeTable[constants.GIRDER_STATIC_ROUTE_ID]
    }

    plugin._loadPlugins(plugins, info)
    root, appconf = info['serverRoot'], info['config']

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
    pluginWebroots = plugin.getPluginWebroots()
    routeTable = Setting().get(constants.SettingKey.ROUTE_TABLE)

    def reconcileRouteTable(routeTable):
        hasChanged = False

        for name in pluginWebroots.keys():
            if name not in routeTable:
                routeTable[name] = os.path.join('/', name)
                hasChanged = True

        if hasChanged:
            Setting().set(constants.SettingKey.ROUTE_TABLE, routeTable)

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

    pluginWebroots = plugin.getPluginWebroots()
    girderWebroot, appconf = configureServer(test, plugins, curConfig)
    routeTable = loadRouteTable(reconcileRoutes=True)

    # Mount Girder
    application = cherrypy.tree.mount(
        girderWebroot, str(routeTable[constants.GIRDER_ROUTE_ID]), appconf)

    # Mount static files
    cherrypy.tree.mount(None, routeTable[constants.GIRDER_STATIC_ROUTE_ID],
                        {'/':
                         # Only turn on if something has been created by 'girder build'
                         {'tools.staticdir.on': os.path.exists(constants.STATIC_ROOT_DIR),
                          'tools.staticdir.dir': constants.STATIC_ROOT_DIR,
                          'request.show_tracebacks': appconf['/']['request.show_tracebacks'],
                          'response.headers.server': 'Girder %s' % __version__,
                          'error_page.default': _errorDefault}})

    # Mount API (special case)
    # The API is always mounted at /api AND at api relative to the Girder root
    cherrypy.tree.mount(girderWebroot.api, '/api', appconf)

    # Mount everything else in the routeTable
    for name, route in six.viewitems(routeTable):
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
        return cherrypy.lib.static.serve_file(self.path, content_type=self.contentType)


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
