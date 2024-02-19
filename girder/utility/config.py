import cherrypy
import logging
import os

from girder.constants import PACKAGE_DIR

logger = logging.getLogger(__name__)


def _mergeConfig(filename):
    """
    Load `filename` into the cherrypy config.
    Also, handle global options by putting them in the root.
    """
    cherrypy._cpconfig.merge(cherrypy.config, filename)
    # When in Sphinx, cherrypy may be mocked and returning None
    global_config = cherrypy.config.pop('global', {}) or {}

    for option, value in global_config.items():
        cherrypy.config[option] = value


def _loadConfigsByPrecedent():
    """
    Load configuration in reverse order of precedent.
    """
    configPaths = [os.path.join(PACKAGE_DIR, 'conf', 'girder.dist.cfg'),
                   os.path.join('/etc', 'girder.cfg'),
                   os.path.join(os.path.expanduser('~'), '.girder', 'girder.cfg')]

    if 'GIRDER_CONFIG' in os.environ:
        configPaths.append(os.environ['GIRDER_CONFIG'])

    for curConfigPath in configPaths:
        if os.path.exists(curConfigPath):
            _mergeConfig(curConfigPath)


def loadConfig():

    _loadConfigsByPrecedent()

    if 'GIRDER_PORT' in os.environ:
        port = int(os.environ['GIRDER_PORT'])
        cherrypy.config['server.socket_port'] = port

    if 'GIRDER_MONGO_URI' in os.environ:
        if 'database' not in cherrypy.config:
            cherrypy.config['database'] = {}
        cherrypy.config['database']['uri'] = os.getenv('GIRDER_MONGO_URI')

    if 'GIRDER_TEST_DB' in os.environ:
        cherrypy.config['database']['uri'] =\
            os.environ['GIRDER_TEST_DB'].replace('.', '_')


def getConfig():
    if 'database' not in cherrypy.config:
        loadConfig()
    # When in Sphinx, cherrypy may be mocked and returning None
    return cherrypy.config or {}


def getServerMode():
    return getConfig()['server']['mode']
