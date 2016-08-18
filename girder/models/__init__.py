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
from girder import logger, logprint
from girder.external.mongodb_proxy import MongoProxy
from girder.utility import config

_dbClients = {}

if pymongo.version_tuple < (3,):
    raise Exception('Your pymongo version (%s) is too old. Please update to '
                    'pymongo 3.x.' % pymongo.version)


def getDbConfig():
    """Get the database configuration values from the cherrypy config."""
    cfg = config.getConfig()
    if 'database' in cfg:
        return cfg['database']
    else:
        return {}


def getDbConnection(uri=None, replicaSet=None, autoRetry=True, **kwargs):
    """
    Get a MongoClient object that is connected to the configured database.
    We lazy-instantiate a module-level singleton, the MongoClient objects
    manage their own connection pools internally. Any extra kwargs you pass to
    this method will be passed through to the MongoClient.

    :param uri: if specified, connect to this mongo db rather than the one in
                the config.
    :param replicaSet: if uri is specified, use this replica set.
    :param autoRetry: if this connection should automatically retry operations
        in the event of an AutoReconnect exception. If you're testing the
        connection, set this to False. If disabled, this also will not cache
        the mongo client, so make sure to only disable if you're testing a
        connection.
    :type autoRetry: bool
    """
    global _dbClients

    origKey = (uri, replicaSet)
    if origKey in _dbClients:
        return _dbClients[origKey]

    if uri is None or uri == '':
        dbConf = getDbConfig()
        uri = dbConf.get('uri')
        replicaSet = dbConf.get('replica_set')
    clientOptions = {
        # This is the maximum time between when we fetch data from a cursor.
        # If it times out, the cursor is lost and we can't reconnect.  If it
        # isn't set, we have issues with replica sets when the primary goes
        # down.  This value can be overridden in the mongodb uri connection
        # string with the socketTimeoutMS.
        'socketTimeoutMS': 60000,
        'connectTimeoutMS': 20000,
        'serverSelectionTimeoutMS': 20000,
        'read_preference': ReadPreference.SECONDARY_PREFERRED,
        'replicaSet': replicaSet
    }
    clientOptions.update(kwargs)

    if uri is None:
        dbUriRedacted = 'mongodb://localhost:27017/girder'
        logprint.warning('WARNING: No MongoDB URI specified, using '
                         'the default value')

        client = pymongo.MongoClient(dbUriRedacted, **clientOptions)
    else:
        parts = uri.split('@')
        if len(parts) == 2:
            dbUriRedacted = 'mongodb://' + parts[1]
        else:
            dbUriRedacted = uri

        client = pymongo.MongoClient(uri, **clientOptions)

    # Make sure we can connect to the mongo server at startup
    client.server_info()

    if autoRetry:
        client = MongoProxy(client, logger=logger)
        _dbClients[origKey] = _dbClients[(uri, replicaSet)] = client

    desc = ''
    if replicaSet:
        desc += ', replica set: %s' % replicaSet
    logprint.info('Connected to MongoDB: %s%s' % (dbUriRedacted, desc))
    return client
