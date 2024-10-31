import cherrypy
import logging
import mako
import mimetypes
import os
import sys

from girder import __version__, constants
from girder.utility import config
from girder.utility._cache import _setupCache
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


def create_app(mode: str) -> dict:
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
    # these may be missing or incorrect in the OS. This is idempotent.
    mimetypes.add_type('application/vnd.ms-fontobject', '.eot')
    mimetypes.add_type('application/x-font-ttf', '.ttf')
    mimetypes.add_type('application/font-woff', '.woff')

    curConfig.update(appconf)
    curConfig['server'] = {'mode': mode}

    logging.basicConfig(stream=sys.stdout, level=os.environ.get('LOGLEVEL', 'INFO'))

    logger.info('Running in mode: %s', curConfig['server']['mode'])
    cherrypy.config['engine.autoreload.on'] = mode == ServerMode.DEVELOPMENT
    cherrypy.config.update({
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': ''
    })

    _setupCache(curConfig)

    # Don't import this until after the configs have been read; some module
    # initialization code requires the configuration to be set up.
    from girder.api.api_main import buildApi

    apiRoot = buildApi()
    tree = cherrypy._cptree.Tree()

    info = dict(config=appconf, serverRoot=tree, apiRoot=apiRoot.v1)

    # Mount static files
    tree.mount(None, '', {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.index': 'index.html',
            'tools.staticdir.dir': os.getenv('GIRDER_STATIC_ROOT_DIR', constants.STATIC_ROOT_DIR),
            'request.show_tracebacks': appconf['/']['request.show_tracebacks'],
            'response.headers.server': f'Girder {__version__}',
            'error_page.default': _errorDefault
        }
    })

    # Mount the web API
    tree.mount(apiRoot, '/api', appconf)

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
                        content type will be guessed by the file extension of
                        the 'path' argument.
    """
    return _StaticFileRoute(path, contentType)
