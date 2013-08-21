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
import cherrypy


def getDbConfig():
    """Get the database configuration object from the cherrypy config.
    """
    return cherrypy.config['database']


def getDbConnection():
    """Get a MongoClient object that is connected to the configured
    database.
    """
    db_cfg = getDbConfig()
    if db_cfg['user'] == '':
        _db_uri = 'mongodb://%s:%d' % (db_cfg['host'], db_cfg['port'])
        _db_uri_redacted = _db_uri
    else:
        _db_uri = 'mongodb://%s:%s@%s:%d' % (db_cfg['user'],
                                             db_cfg['password'],
                                             db_cfg['host'],
                                             db_cfg['port'])
        _db_uri_redacted = 'mongodb://%s@%s:%d' % (db_cfg['user'],
                                                   db_cfg['host'],
                                                   db_cfg['port'])

    db_connection = pymongo.MongoClient(_db_uri)
    print "Connected to MongoDB: %s" % _db_uri_redacted
    return db_connection
