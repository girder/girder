import cherrypy
import logging
import os

logger = logging.getLogger(__name__)


def loadConfig():
    # Calling this has the side effect of populating the cherrypy.config object with
    # values from the environment. It is called at import time of the girder package.
    cherrypy.config['server.socket_host'] = os.getenv('GIRDER_HOST', '127.0.0.1')
    cherrypy.config['server.socket_port'] = int(os.getenv('GIRDER_PORT', 8080))
    cherrypy.config['server.thread_pool'] = int(os.getenv('GIRDER_THREAD_POOL', 100))
    cherrypy.config['tools.proxy.on'] = True

    if 'database' not in cherrypy.config:
        cherrypy.config['database'] = {}

    if 'GIRDER_TEST_DB' in os.environ:
        cherrypy.config['database']['uri'] = os.environ['GIRDER_TEST_DB'].replace('.', '_')
    else:
        cherrypy.config['database']['uri'] = os.getenv(
            'GIRDER_MONGO_URI', 'mongodb://localhost:27017/girder')
        cherrypy.config['database']['replica_set'] = os.getenv('GIRDER_MONGO_REPLICA_SET')


def getConfig():
    if 'database' not in cherrypy.config:
        loadConfig()
    # When in Sphinx, cherrypy may be mocked and returning None
    return cherrypy.config or {}


def getServerMode():
    return getConfig()['server']['mode']
