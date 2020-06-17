# -*- coding: utf-8 -*-
from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = None

__license__ = 'Apache 2.0'

import cherrypy
import functools
import io
import logging
import logging.handlers
import os
import sys
import traceback

from girder.constants import LOG_ROOT, MAX_LOG_SIZE, LOG_BACKUP_COUNT, TerminalColor
from girder.utility import config, mkdir
from girder.utility._cache import cache, requestCache, rateLimitBuffer

_quiet = False
_originalStdOut = sys.stdout
_originalStdErr = sys.stderr
auditLogger = logging.getLogger('girder_audit')
auditLogger.setLevel(logging.INFO)
logger = logging.getLogger('girder')
logger.setLevel(logging.DEBUG)  # Pass everything; let filters handle level-based filtering
config.loadConfig()  # Populate the config info at import time


class LogLevelFilter:
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
            '  Request URL: %s %s' % (cherrypy.request.method.upper(), cherrypy.url()),
            '  Query string: ' + cherrypy.request.query_string,
            '  Remote IP: ' + cherrypy.request.remote.ip,
            '  Request UID: ' + getattr(cherrypy.request, 'girderRequestUid', '[none]')
        ))
        return ('%s\n'
                'Additional info:\n'
                '%s' % (super().formatException(exc), info))

    def format(self, record, *args, **kwargs):
        if hasattr(record, 'name') and hasattr(record, 'message'):
            if (record.name.startswith('cherrypy.access')
                    or record.name.startswith('cherrypy.error')):
                return record.message
        return super().format(record, *args, **kwargs)


class StreamToLogger:
    """
    Redirect a file-like stream to a logger.
    """

    def __init__(self, stream, logger, level):
        self.stream = stream
        self.logger = logger
        self.level = level
        self.logger._girderLogHandlerOutput = False
        # This class is intended to override a default stream like sys.stdout
        # and sys.stderr and send that information to both the original stream
        # and the logger method.  However, we want to preserve as much
        # functionality for stdout and stderr as possible, so that other
        # modules that send data to them can do so without a problem.  The only
        # method we really need to override is write, but we cannot mutate the
        # write method on the stream itself, so we replace the stream with this
        # custom class.  To preserve the stream methods, all of them get added
        # to our class instance except private and built-in methods, which, in
        # python, begin with _.
        #     Fundamentally, this lets our stream replacement handle functions
        # flush, writeline, and others without having to enumerate them
        # individually.
        for key in dir(stream):
            # It's possible for a file-like object to have name appear in dir(stream) but not
            # actually be an attribute, thus using a default with getattr is required.
            # See https://github.com/GrahamDumpleton/mod_wsgi/issues/184 for more.
            if (key != 'write'
                    and not key.startswith('_')
                    and (callable(getattr(stream, key, None))
                         or isinstance(
                             getattr(stream, key, None),
                             (bytes, str, int, bool)))):
                setattr(self, key, getattr(stream, key))

    def write(self, buf):
        if not self.logger._girderLogHandlerOutput:
            self.logger._girderLogHandlerOutput = True
            self.stream.write(buf)
            for line in buf.rstrip().splitlines():
                self.logger.log(self.level, line.rstrip())
            self.logger._girderLogHandlerOutput = False


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


def _attachFileLogHandlers():
    """
    Sets up the Girder logger.
    """
    global _quiet

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

    # Allow minimum log level to be set via config file
    level = logging.INFO
    if logCfg.get('log_level') and isinstance(getattr(logging, logCfg['log_level'], None), int):
        level = getattr(logging, logCfg['log_level'])

    logSize = MAX_LOG_SIZE
    if logCfg.get('log_max_size'):
        sizeValue = logCfg['log_max_size']
        sizeUnits = {'kb': 1024, 'Mb': 1024 ** 2, 'Gb': 1024 ** 3}
        if sizeValue[-2:] in sizeUnits:
            logSize = int(sizeValue[:-2].strip()) * sizeUnits[sizeValue[-2:]]
        else:
            logSize = int(sizeValue)
    backupCount = int(logCfg.get('log_backup_count', LOG_BACKUP_COUNT))

    fmt = LogFormatter('[%(asctime)s] %(levelname)s: %(message)s')
    infoMaxLevel = logging.INFO
    # Create log handlers
    if logPaths['error'] != logPaths['info']:
        eh = logging.handlers.RotatingFileHandler(
            logPaths['error'], maxBytes=logSize, backupCount=backupCount)
        eh.setLevel(level)
        eh.addFilter(LogLevelFilter(min=logging.WARNING, max=logging.CRITICAL))
        eh._girderLogHandler = 'error'
        eh.setFormatter(fmt)
        logger.addHandler(eh)
        # Record cherrypy errors in our logs, too
        cherrypy.log.error_log.addHandler(eh)
    else:
        infoMaxLevel = logging.CRITICAL

    if isinstance(getattr(logging, logCfg.get('log_max_info_level', ''), None), int):
        infoMaxLevel = getattr(logging, logCfg['log_max_info_level'])
    ih = logging.handlers.RotatingFileHandler(
        logPaths['info'], maxBytes=logSize, backupCount=backupCount)
    ih.setLevel(level)
    ih.addFilter(LogLevelFilter(min=logging.DEBUG, max=infoMaxLevel))
    ih._girderLogHandler = 'info'
    ih.setFormatter(fmt)
    logger.addHandler(ih)
    # Record cherrypy errors in our logs, too
    cherrypy.log.error_log.addHandler(ih)

    # Log http accesses to the screen and/or the info log.
    accessLog = logCfg.get('log_access', 'screen')
    if not isinstance(accessLog, (tuple, list, set)):
        accessLog = [accessLog]
    if _quiet or ('screen' not in accessLog and 'stdout' not in accessLog):
        cherrypy.config.update({'log.screen': False})
    if 'info' in accessLog:
        cherrypy.log.access_log.addHandler(ih)

    return logger


def logStdoutStderr(force=False):
    if _originalStdOut == sys.stdout or force:
        sys.stdout = StreamToLogger(_originalStdOut, logger, logging.INFO)
        sys.stderr = StreamToLogger(_originalStdErr, logger, logging.ERROR)


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
    data = io.StringIO()
    kwargs = (kwargs or {}).copy()
    level = kwargs.pop('level', logging.DEBUG)
    color = kwargs.pop('color', None)
    exc_info = kwargs.pop('exc_info', None)
    kwargs['file'] = data
    print(*args, **kwargs)
    data = data.getvalue().rstrip()
    if exc_info and not isinstance(exc_info, tuple):
        exc_info = sys.exc_info()
        data += '\n' + ''.join(traceback.format_exception(*exc_info)).rstrip()
    logger.log(level, data)
    if not _quiet:
        if color:
            data = getattr(TerminalColor, color)(data)
        _originalStdOut.write('%s\n' % data)
        _originalStdOut.flush()


def _setupCache():
    """
    Setup caching based on configuration file.

    Cache backends are forcibly replaced because Girder initially configures
    the regions with the null backends.
    """
    curConfig = config.getConfig()

    if curConfig['cache']['enabled']:
        # Replace existing backend, this is necessary
        # because they're initially configured with the null backend
        cacheConfig = {
            'cache.global.replace_existing_backend': True,
            'cache.request.replace_existing_backend': True
        }

        curConfig['cache'].update(cacheConfig)

        cache.configure_from_config(curConfig['cache'], 'cache.global.')
        requestCache.configure_from_config(curConfig['cache'], 'cache.request.')
    else:
        # Reset caches back to null cache (in the case of server teardown)
        cache.configure(backend='dogpile.cache.null', replace_existing_backend=True)
        requestCache.configure(backend='dogpile.cache.null', replace_existing_backend=True)

    # Although the rateLimitBuffer has no pre-existing backend, this method may be called multiple
    # times in testing (where caches were already configured)
    rateLimitBuffer.configure(backend='dogpile.cache.memory', replace_existing_backend=True)


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
