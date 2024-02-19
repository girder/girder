import cherrypy
from dataclasses import dataclass
import logging
import mako
import mimetypes
import os
import sys

from girder import __version__, _setupCache, constants, plugin
from girder.models.setting import Setting
from girder.settings import SettingKey
from girder.utility import config
from girder.constants import ServerMode

logger = logging.getLogger(__name__)

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
                routeTable[name] = f'/{name.lstrip("/")}'
                hasChanged = True

        if hasChanged:
            Setting().set(SettingKey.ROUTE_TABLE, routeTable)

        return routeTable

    if reconcileRoutes:
        routeTable = reconcileRouteTable(routeTable)

    return {name: route for (name, route) in routeTable.items() if route}


@dataclass
class AppInfo:
    config: dict
    serverRoot: cherrypy._cptree.Tree
    apiRoot: cherrypy._cptree.Tree


def create_app(mode: str) -> AppInfo:
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
    curConfig['server']['mode'] = mode

    logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', 'INFO'))

    logger.info('Running in mode: %s', curConfig['server']['mode'])
    cherrypy.config['engine.autoreload.on'] = mode == ServerMode.DEVELOPMENT
    cherrypy.config.update({
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': ''
    })

    _setupCache()

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api.api_main import buildApi

    apiRoot = buildApi()
    tree = cherrypy._cptree.Tree()

    routeTable = loadRouteTable()
    info = AppInfo(
        config=appconf,
        serverRoot=tree,
        apiRoot=apiRoot.v1,
    )

    pluginWebroots = plugin.getPluginWebroots()
    routeTable = loadRouteTable(reconcileRoutes=True)

    # Mount static files
    tree.mount(None, routeTable[constants.GIRDER_ROUTE_ID], {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.index': 'index.html',
            'tools.staticdir.dir': constants.STATIC_ROOT_DIR,
            'request.show_tracebacks': appconf['/']['request.show_tracebacks'],
            'response.headers.server': f'Girder {__version__}',
            'error_page.default': _errorDefault
        }
    })

    # Mount API
    tree.mount(
        apiRoot,
        f"{routeTable[constants.GIRDER_ROUTE_ID].rstrip('/')}/api",
        appconf
    )

    if routeTable[constants.GIRDER_ROUTE_ID] != '/':
        # Mount API (special case)
        # The API is always mounted at /api AND at api relative to the Girder root
        tree.mount(apiRoot, '/api', appconf)

    # Mount everything else in the routeTable
    for name, route in routeTable.items():
        if name != constants.GIRDER_ROUTE_ID and name in pluginWebroots:
            tree.mount(pluginWebroots[name], route, appconf)

    return info


class _StaticFileRoute:
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
