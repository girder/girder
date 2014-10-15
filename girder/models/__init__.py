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

from girder.utility import config
from girder.constants import TerminalColor

_db_connection = None


def getDbConfig():
    """Get the database configuration uri from the cherrypy config."""
    cfg = config.getConfig()
    if 'database' in cfg:
        return cfg['database']['uri']
    else:
        return None


def getDbConnection():
    """Get a MongoClient object that is connected to the configured
    database. Lazy getter so we only have one connection per instance."""
    global _db_connection

    if _db_connection is not None:
        return _db_connection

    _db_uri = getDbConfig()
    if _db_uri is None:
        _db_uri_redacted = 'mongodb://localhost:27017/girder'
        print(TerminalColor.warning('WARNING: No MongoDB URI specified, using '
                                    'the default value'))
        _db_connection = pymongo.MongoClient(_db_uri_redacted)
    else:
        parts = _db_uri.split('@')
        if len(parts) == 2:
            _db_uri_redacted = 'mongodb://' + parts[1]
        else:
            _db_uri_redacted = _db_uri
        _db_connection = pymongo.MongoClient(_db_uri)
    print(TerminalColor.info('Connected to MongoDB: {}'
                             .format(_db_uri_redacted)))
    return _db_connection
