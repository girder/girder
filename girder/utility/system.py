#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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
import psutil
import six
import socket
import threading
import time

import girder
from girder import logger
from girder.models import getDbConnection


def _objectToDict(obj):
    """
    Convert an object to a dictionary.  Any non-private attribute that is an
    integer, float, or string is returned in the dictionary.

    :param obj: a python object or class.
    :returns: a dictionary of values for the object.
    """
    return {key: getattr(obj, key) for key in dir(obj) if
            not key.startswith('_') and
            isinstance(getattr(obj, key),
                       tuple([float, tuple] + list(six.string_types) +
                             list(six.integer_types)))}


def _computeSlowStatus(process, status, db):
    status['diskPartitions'] = [_objectToDict(part) for part in
                                psutil.disk_partitions()]
    try:
        # This fails in certain environments, so guard it
        status['diskIO'] = _objectToDict(psutil.disk_io_counters())
    except Exception:
        pass
    # Report on the disk usage where the script is located
    if hasattr(girder, '__file__'):
        status['girderPath'] = os.path.abspath(girder.__file__)
        status['girderDiskUsage'] = _objectToDict(
            psutil.disk_usage(status['girderPath']))
    # Report where our logs are and how much space is available for them
    status['logs'] = []
    for handler in logger.handlers:
        try:
            logInfo = {'path': handler.baseFilename}
            logInfo['diskUsage'] = _objectToDict(
                psutil.disk_usage(logInfo['path']))
            status['logs'].append(logInfo)
        except Exception:
            # If we can't read information about the log, don't throw an
            # exception
            pass
    status['mongoDbStats'] = db.command('dbStats')
    try:
        # I don't know if this will work with a sharded database, so guard
        # it and don't throw an exception
        status['mongoDbPath'] = getDbConnection().admin.command(
            'getCmdLineOpts')['parsed']['storage']['dbPath']
        status['mongoDbDiskUsage'] = _objectToDict(
            psutil.disk_usage(status['mongoDbPath']))
    except Exception:
        pass

    status['processDirectChildrenCount'] = len(process.children())
    status['processAllChildrenCount'] = len(process.children(True))
    status['openFiles'] = [_objectToDict(file) for file in
                           process.open_files()]
    # I'd rather see textual names for the family and type of connections,
    # so make a lookup table for them
    connFamily = {getattr(socket, key): key for key in dir(socket)
                  if key.startswith('AF_')}
    connType = {getattr(socket, key): key for key in dir(socket)
                if key.startswith('SOCK_')}
    connections = []
    for conn in process.connections():
        connDict = _objectToDict(conn)
        connDict.pop('raddr', None)
        connDict.pop('laddr', None)
        connDict['family'] = connFamily.get(connDict['family'],
                                            connDict['family'])
        connDict['type'] = connType.get(connDict['type'], connDict['type'])
        connections.append(connDict)
    status['connections'] = connections
    if hasattr(process, 'io_counters'):
        status['ioCounters'] = _objectToDict(process.io_counters())

    status['cherrypyThreads'] = {}
    for threadId in cherrypy.tools.status.seenThreads:
        info = cherrypy.tools.status.seenThreads[threadId].copy()
        if 'end' in info:
            info['duration'] = info['end'] - info['start']
            info['idle'] = time.time() - info['end']
        status['cherrypyThreads'][threadId] = info


def getStatus(mode='basic', user=None):
    """
    Get a dictionary of status information regarding the Girder server.

    :param mode: 'basic' returns values available to any anonymous user.
        'quick' returns only values that are cheap to acquire.
        'slow' provides all of that information and adds additional
    :param user: a user record.  Must have admin access to get anything other
                 than basic mode.
    :returns: a status dictionary.
    """
    isAdmin = (user is not None and user['admin'])

    status = {}
    status['bootTime'] = psutil.boot_time()
    status['currentTime'] = time.time()
    process = psutil.Process(os.getpid())
    status['processStartTime'] = process.create_time()

    if mode in ('quick', 'slow') and isAdmin:
        status['virtualMemory'] = _objectToDict(psutil.virtual_memory())
        status['swap'] = _objectToDict(psutil.swap_memory())
        status['cpuCount'] = psutil.cpu_count()

        status['processMemory'] = _objectToDict(process.memory_info())
        status['processName'] = process.name()
        status['cmdline'] = process.cmdline()
        status['exe'] = process.exe()
        status['cwd'] = process.cwd()
        status['userName'] = process.username()
        status['processCpuTimes'] = _objectToDict(process.cpu_times())
        db = getDbConnection().get_database()
        status['mongoBuildInfo'] = db.command('buildInfo')
        status['cherrypyThreadsMaxUsed'] = len(
            cherrypy.tools.status.seenThreads)
        status['cherrypyThreadsInUse'] = len([
            True for threadId in cherrypy.tools.status.seenThreads
            if 'end' not in cherrypy.tools.status.seenThreads[threadId]])
        status['cherrypyThreadPoolSize'] = cherrypy.server.thread_pool

    if mode == 'slow' and isAdmin:
        _computeSlowStatus(process, status, db)
    return status


def formatSize(sizeBytes):
    """
    Format a size in bytes into a human-readable string with metric unit
    prefixes.

    :param sizeBytes: the size in bytes to format.
    :returns: the formatted size string.
    """
    suffixes = ['B', 'kB', 'MB', 'GB', 'TB']
    if sizeBytes < 20000:
        return '%d %s' % (sizeBytes, suffixes[0])
    idx = 0
    sizeVal = float(sizeBytes)
    while sizeVal >= 1024 and idx + 1 < len(suffixes):
        sizeVal /= 1024
        idx += 1
    if sizeVal < 10:
        precision = 3
    elif sizeVal < 100:
        precision = 2
    else:
        precision = 1
    return '%.*f %s' % (precision, sizeVal, suffixes[idx])


# This class is used to monitor which threads in cherrypy are actively serving
# responses, and what each was last used for.  It is based on the example at
# http://tools.cherrypy.org/wiki/StatusTool, but has changes to handle yield-
# based responses.
class StatusMonitor(cherrypy.Tool):
    """Register the status of each thread."""

    def __init__(self):
        self._point = 'on_start_resource'
        self._name = 'status'
        self._priority = 50
        self.seenThreads = {}

    def callable(self):
        threadId = threading.current_thread().ident
        self.seenThreads[threadId] = {
            'start': cherrypy.response.time, 'url': cherrypy.url()}

    def unregister(self):
        """Unregister the current thread."""
        threadID = threading.current_thread().ident
        if threadID in self.seenThreads:
            self.seenThreads[threadID]['end'] = time.time()

    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.request.hooks.attach('on_end_request', self.unregister)


cherrypy.tools.status = StatusMonitor()
cherrypy.config.update({"tools.status.on": True})
