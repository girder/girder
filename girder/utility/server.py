# -*- coding: utf-8 -*-
import cherrypy
import mako
import mimetypes
import os
import six

import girder.events
from girder import constants, logprint, __version__, logStdoutStderr, _setupCache
from girder.models.setting import Setting
from girder import plugin
from girder.settings import SettingKey
from girder.utility import config
from girder.constants import ServerMode
from . import webroot

with open(os.path.join(os.path.dirname(__file__), 'error.mako')) as f:
    _errorTemplate = f.read()


def _errorDefault(status, message, *args, **kwargs):
    """
    This is used to render error pages outside of the normal Girder app, such as
    404's. This overrides the default cherrypy error pages.
    """
    return mako.template.Template(_errorTemplate).render(status=status, message=message)


def getApiRoot():
    return config.getConfig()['server']['api_root']


def getStaticPublicPath():
    return config.getConfig()['server']['static_public_path']


def configureServer(mode=None, plugins=None, curConfig=None):
    """
    Function to setup the cherrypy server. It configures it, but does
    not actually start it.

    :param mode: The server mode to start in.
    :type mode: string
    :param plugins: If you wish to start the server with a custom set of
        plugins, pass this as a list of plugins to load. Otherwise,
        all installed plugins will be loaded.
    :param curConfig: The configuration dictionary to update.
    """
    if curConfig is None:
        curConfig = config.getConfig()

    appconf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'request.show_tracebacks': mode == ServerMode.TESTING,
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
    if mode:
        curConfig['server']['mode'] = mode

    logprint.info('Running in mode: ' + curConfig['server']['mode'])
    cherrypy.config['engine.autoreload.on'] = mode == ServerMode.DEVELOPMENT

    _setupCache()

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api import api_main

    root = webroot.Webroot()
    api_main.addApiToNode(root)

    girder.events.setupDaemon()
    cherrypy.engine.subscribe('start', girder.events.daemon.start)
    cherrypy.engine.subscribe('stop', girder.events.daemon.stop)

    routeTable = loadRouteTable()
    info = {
        'config': appconf,
        'serverRoot': root,
        'serverRootPath': routeTable[constants.GIRDER_ROUTE_ID],
        'apiRoot': root.api.v1,
    }

    plugin._loadPlugins(info, plugins)
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
    routeTable = Setting().get(SettingKey.ROUTE_TABLE)

    def reconcileRouteTable(routeTable):
        hasChanged = False

        # Migration for the removed static root setting
        if 'core_static_root' in routeTable:
            del routeTable['core_static_root']
            hasChanged = True

        for name in pluginWebroots.keys():
            if name not in routeTable:
                routeTable[name] = os.path.join('/', name)
                hasChanged = True

        if hasChanged:
            Setting().set(SettingKey.ROUTE_TABLE, routeTable)

        return routeTable

    if reconcileRoutes:
        routeTable = reconcileRouteTable(routeTable)

    return {name: route for (name, route) in six.viewitems(routeTable) if route}


def setup(mode=None, plugins=None, curConfig=None):
    """
    Configure and mount the Girder server and plugins under the
    appropriate routes.

    See ROUTE_TABLE setting.

    :param mode: The server mode to start in.
    :type mode: string
    :param plugins: List of plugins to enable.
    :param curConfig: The config object to update.
    """
    logStdoutStderr()

    pluginWebroots = plugin.getPluginWebroots()
    girderWebroot, appconf = configureServer(mode, plugins, curConfig)
    routeTable = loadRouteTable(reconcileRoutes=True)

    # Mount Girder
    application = cherrypy.tree.mount(
        girderWebroot, str(routeTable[constants.GIRDER_ROUTE_ID]), appconf)

    # Mount static files
    cherrypy.tree.mount(None, '/static',
                        {'/':
                         {'tools.staticdir.on': True,
                          'tools.staticdir.dir': os.path.join(constants.STATIC_ROOT_DIR),
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
