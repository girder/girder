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

__version__ = '2.2.0'
__license__ = 'Apache 2.0'


_quiet = False


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
    when an exception happens.  Cherrypy access logs are passed through without
    change.
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

    def format(self, record, *args, **kwargs):
        if hasattr(record, 'name') and hasattr(record, 'message'):
            if record.name.startswith('cherrypy.access'):
                return record.message
        return super(LogFormatter, self).format(record, *args, **kwargs)


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
    global _quiet

    logger = logging.getLogger('girder')
    cfg = config.getConfig()
    logCfg = cfg.get('logging', {})

    # If we are asked to be quiet, set a global flag so that logprint doesn't
    # have to get the configuration settings every time it is used.
    if logCfg.get('log_quiet') is True:
        _quiet = True

    logPaths = getLogPaths()
    # Ensure log paths are valid
    logDirs = [
        logPaths['root'],
        os.path.dirname(logPaths['info']),
        os.path.dirname(logPaths['error'])
    ]
    for logDir in logDirs:
        mkdir(logDir)

    # Set log level
    level = logging.INFO
    if logCfg.get('log_level') and isinstance(getattr(logging, logCfg['log_level'], None), int):
        level = getattr(logging, logCfg['log_level'])
    logger.setLevel(logging.DEBUG if level is None else level)

    logSize = MAX_LOG_SIZE
    if logCfg.get('log_max_size'):
        sizeValue = logCfg['log_max_size']
        sizeUnits = {'kb': 1024, 'Mb': 1024 ** 2, 'Gb': 1024 ** 3}
        if sizeValue[-2:] in sizeUnits:
            logSize = int(sizeValue[:-2].strip()) * sizeUnits[sizeValue[-2:]]
        else:
            logSize = int(sizeValue)
    backupCount = int(logCfg.get('log_backup_count', LOG_BACKUP_COUNT))

    # Remove extant log handlers (this allows this function to called multiple
    # times)
    for handler in list(logger.handlers):
        if hasattr(handler, '_girderLogHandler'):
            logger.removeHandler(handler)
            cherrypy.log.access_log.removeHandler(handler)

    fmt = LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
    # Create log handlers
    if logPaths['error'] != logPaths['info']:
        eh = logging.handlers.RotatingFileHandler(
            logPaths['error'], maxBytes=logSize, backupCount=backupCount)
        eh.setLevel(level)
        eh.addFilter(LogLevelFilter(min=logging.WARNING, max=logging.CRITICAL))
        eh._girderLogHandler = 'error'
        eh.setFormatter(fmt)
        logger.addHandler(eh)

    ih = logging.handlers.RotatingFileHandler(
        logPaths['info'], maxBytes=logSize, backupCount=backupCount)
    ih.setLevel(level)
    ih.addFilter(LogLevelFilter(min=logging.DEBUG, max=logging.INFO))
    ih._girderLogHandler = 'info'
    ih.setFormatter(fmt)
    logger.addHandler(ih)

    # Log http accesses to the screen and/or the info log.
    accessLog = logCfg.get('log_access', 'screen')
    if not isinstance(accessLog, (tuple, list, set)):
        accessLog = [accessLog]
    if _quiet or ('screen' not in accessLog and 'stdout' not in accessLog):
        cherrypy.config.update({'log.screen': False})
    if 'info' in accessLog:
        cherrypy.log.access_log.addHandler(ih)

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
    if not _quiet:
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
