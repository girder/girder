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
import functools
import logging
import logging.handlers
import os
import six
import sys
import traceback


from girder.constants import LOG_ROOT, MAX_LOG_SIZE, LOG_BACKUP_COUNT, \
    TerminalColor
from girder.utility import config, mkdir

__version__ = '2.1.0'
__license__ = 'Apache 2.0'


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


def logprint(*args, **kwargs):
    """
    Send a message to both stdout and the appropriate logs.  This behaves like
    Python3's print statement, plus takes additional named parameters:

    :param level: the log level.  This determines which log handlers will store
        the log message.  The log is always sent to stdout.
    :param color: one of the constants.TerminalColor values or None.
    :param exc_info: None to not print exception information.  True for the
        last exception, or a tuple of exception information.
    """
    data = six.StringIO()
    kwargs = (kwargs or {}).copy()
    level = kwargs.pop('level', logging.DEBUG)
    color = kwargs.pop('color', None)
    exc_info = kwargs.pop('exc_info', None)
    kwargs['file'] = data
    six.print_(*args, **kwargs)
    data = data.getvalue().rstrip()
    if exc_info and not isinstance(exc_info, tuple):
        exc_info = sys.exc_info()
        data += '\n' + ''.join(traceback.format_exception(*exc_info)).rstrip()
    logger.log(level, data)
    if color:
        data = getattr(TerminalColor, color)(data)
    six.print_(data, flush=True)

# Expose common logging levels and colors as methods of logprint.
logprint.info = functools.partial(logprint, level=logging.INFO, color='info')
logprint.warning = functools.partial(
    logprint, level=logging.WARNING, color='warning')
logprint.error = functools.partial(
    logprint, level=logging.ERROR, color='error')
logprint.success = functools.partial(
    logprint, level=logging.INFO, color='success')
logprint.critical = functools.partial(
    logprint, level=logging.CRITICAL, color='error')
logprint.debug = logprint
logprint.exception = functools.partial(
    logprint, level=logging.ERROR, color='error', exc_info=True)


# alias girder.plugin => girder.utility.plugin_utilities
from girder.utility import plugin_utilities as plugin  # noqa
