#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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
import logging.handlers
import os


from girder.constants import LOG_ROOT, MAX_LOG_SIZE, LOG_BACKUP_COUNT
from girder.utility import config, mkdir

__version__ = '1.5.2'


class LogLevelFilter(object):
    """
    Filter log records based on whether they are between a min and max level.
    """
    def __init__(self, min, max):
        self.minLevel = min
        self.maxLevel = max

    def filter(self, logRecord):
        level = logRecord.levelno
        return self.maxLevel >= level >= self.minLevel


class LogFormatter(logging.Formatter):
    """
    Custom formatter that adds useful information about the request to the logs
    when an exception happens.
    """
    def formatException(self, exc):
        info = '\n'.join((
            '  Request URL: %s %s' % (cherrypy.request.method.upper(),
                                      cherrypy.url()),
            '  Query string: ' + cherrypy.request.query_string,
            '  Remote IP: ' + cherrypy.request.remote.ip
        ))
        return ('%s\n'
                'Additional info:\n'
                '%s' % (logging.Formatter.formatException(self, exc), info))


def getLogPaths():
    """
    Return the paths to the error and info log files. These are returned as
    a dict with "error" and "info" keys that point to the respective file,
    as well as a "root" key pointing to the log root directory.
    """
    cfg = config.getConfig()
    logCfg = cfg.get('logging', {})
    root = os.path.expanduser(logCfg.get('log_root', LOG_ROOT))

    return {
        'root': root,
        'error': logCfg.get('error_log_file', os.path.join(root, 'error.log')),
        'info': logCfg.get('info_log_file', os.path.join(root, 'info.log'))
    }


def _setupLogger():
    """
    Sets up the Girder logger.
    """
    logger = logging.getLogger('girder')
    logger.setLevel(logging.DEBUG)

    logPaths = getLogPaths()

    # Ensure log paths are valid
    logDirs = [
        logPaths['root'],
        os.path.dirname(logPaths['info']),
        os.path.dirname(logPaths['error'])
    ]
    for logDir in logDirs:
        mkdir(logDir)

    eh = logging.handlers.RotatingFileHandler(
        logPaths['error'], maxBytes=MAX_LOG_SIZE, backupCount=LOG_BACKUP_COUNT)
    eh.setLevel(logging.WARNING)
    eh.addFilter(LogLevelFilter(min=logging.WARNING, max=logging.CRITICAL))
    ih = logging.handlers.RotatingFileHandler(
        logPaths['info'], maxBytes=MAX_LOG_SIZE, backupCount=LOG_BACKUP_COUNT)
    ih.setLevel(logging.INFO)
    ih.addFilter(LogLevelFilter(min=logging.DEBUG, max=logging.INFO))

    fmt = LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
    eh.setFormatter(fmt)
    ih.setFormatter(fmt)

    logger.addHandler(eh)
    logger.addHandler(ih)
    return logger

logger = _setupLogger()

# alias girder.plugin => girder.utility.plugin_utilities
from girder.utility import plugin_utilities as plugin  # noqa
