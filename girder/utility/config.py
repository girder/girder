# -*- coding: utf-8 -*-
import cherrypy
import os

import girder
from girder.constants import PACKAGE_DIR


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
    # TODO: Deprecated, remove in a later version
    def _printConfigurationWarning():
        girder.logprint.warning(
            'Detected girder.local.cfg, this location is no longer supported.\n'
            'For supported locations, see '
            'https://girder.readthedocs.io/en/stable/configuration.html#configuration')

    if os.path.exists(os.path.join(PACKAGE_DIR, 'conf', 'girder.local.cfg')):
        # This can't use logprint since configuration is loaded before initialization.
        # Note this also won't be displayed when starting other services that don't start a CherryPy
        # server such as girder mount or girder sftpd.
        cherrypy.engine.subscribe('start', _printConfigurationWarning)

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
