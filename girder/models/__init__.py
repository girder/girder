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

import pymongo

from pymongo.read_preferences import ReadPreference
from girder.utility import config
from girder.constants import TerminalColor

_dbClient = None


def getDbConfig():
    """Get the database configuration values from the cherrypy config."""
    cfg = config.getConfig()
    if 'database' in cfg:
        return cfg['database']
    else:
        return {}


def getDbConnection():
    """
    Get a MongoClient object that is connected to the configured database.
    We lazy-instantiate a module-level singleton, the MongoClient objects
    manage their own connection pools internally.
    """
    global _dbClient

    if _dbClient is not None:
        return _dbClient

    dbConf = getDbConfig()
    if not dbConf.get('uri'):
        dbUriRedacted = 'mongodb://localhost:27017/girder'
        print(TerminalColor.warning('WARNING: No MongoDB URI specified, using '
                                    'the default value'))

        _dbClient = pymongo.MongoClient(dbUriRedacted)
    else:
        parts = dbConf['uri'].split('@')
        if len(parts) == 2:
            dbUriRedacted = 'mongodb://' + parts[1]
        else:
            dbUriRedacted = dbConf['uri']

        replicaSet = dbConf.get('replica_set')

        if replicaSet:
            _dbClient = pymongo.MongoReplicaSetClient(
                dbConf['uri'], replicaSet=replicaSet)
            _dbClient.read_preference = ReadPreference.SECONDARY_PREFERRED
        else:
            _dbClient = pymongo.MongoClient(dbConf['uri'])
    print(TerminalColor.info('Connected to MongoDB: {}'
                             .format(dbUriRedacted)))
    return _dbClient
