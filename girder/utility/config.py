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
from girder import constants
import os
import re


def _mergeConfig(filename):
    '''
    Load `filename` into the cherrypy config.
    Also, handle global options by putting them in the root.
    '''
    cherrypy._cpconfig.merge(cherrypy.config, filename)
    global_config = cherrypy.config.pop('global', {})

    for option, value in global_config.iteritems():
        cherrypy.config[option] = value


def loadConfig():
    _mergeConfig(
        os.path.join(constants.ROOT_DIR, 'girder', 'conf', 'girder.dist.cfg'))

    local = os.path.join(constants.ROOT_DIR, 'girder', 'conf',
                         'girder.local.cfg')
    if os.path.exists(local):
        _mergeConfig(local)
    else:
        print constants.TerminalColor.warning(
            'WARNING: "{}" does not exist.'.format(local))

    # The PORT environment variable will override the config port
    if 'PORT' in os.environ:
        port = int(os.environ['PORT'])
        print 'Using PORT env value ({})'.format(port)
        cherrypy.config['server.socket_port'] = port

    # The MONGOLAB_URI should override the database config
    if os.getenv('MONGOLAB_URI'):  # for Heroku
        matcher = re.match(r"mongodb://(.+):(.+)@(.+):(.+)/(.+)",
                           os.getenv('MONGOLAB_URI'))
        res = {'user': matcher.group(1),
               'password': matcher.group(2),
               'host': matcher.group(3),
               'port': int(matcher.group(4)),
               'database': matcher.group(5)}
        cherrypy.config['database'] = res

    if 'GIRDER_TEST_DB' in os.environ:
        cherrypy.config['database']['database'] =\
            os.environ['GIRDER_TEST_DB'].replace('.', '_')


def getConfig():
    if 'database' not in cherrypy.config:
        loadConfig()
    return cherrypy.config
