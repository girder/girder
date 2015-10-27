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

import cherrypy
import os
import six

from girder.constants import PACKAGE_DIR


def _mergeConfig(filename):
    """
    Load `filename` into the cherrypy config.
    Also, handle global options by putting them in the root.
    """
    cherrypy._cpconfig.merge(cherrypy.config, filename)
    global_config = cherrypy.config.pop('global', {})

    for option, value in six.viewitems(global_config):
        cherrypy.config[option] = value


def _loadConfigsByPrecedent():
    """
    Load configuration in reverse order of precedent.
    """
    configPaths = []
    configPaths.append(
        os.path.join(PACKAGE_DIR, 'conf', 'girder.dist.cfg'))
    configPaths.append(
        os.path.join(PACKAGE_DIR, 'conf', 'girder.local.cfg'))
    configPaths.append(
        os.path.join('/etc', 'girder.cfg'))
    configPaths.append(
        os.path.join(os.path.expanduser('~'), '.girder', 'girder.cfg'))
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
    return cherrypy.config
