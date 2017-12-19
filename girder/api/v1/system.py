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

import cherrypy.process.plugins
import datetime
import errno
import girder
import json
import six
import os
import logging

from girder.api import access
from girder.constants import GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID, \
    SettingKey, TokenScope, ACCESS_FLAGS, VERSION
from girder.exceptions import GirderException, ResourcePathNotFound, RestException
from girder.models.group import Group
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.utility import config, install, plugin_utilities, system
from girder.utility.progress import ProgressContext
from ..describe import API_VERSION, Description, autoDescribeRoute
from ..rest import Resource

ModuleStartTime = datetime.datetime.utcnow()
LOG_BUF_SIZE = 65536


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """
    def __init__(self):
        super(System, self).__init__()
        self.resourceName = 'system'
        self.route('DELETE', ('setting',), self.unsetSetting)
        self.route('GET', ('version',), self.getVersion)
        self.route('GET', ('configuration',), self.getConfigurationOption)
        self.route('GET', ('setting',), self.getSetting)
        self.route('GET', ('plugins',), self.getPlugins)
        self.route('GET', ('access_flag',), self.getAccessFlags)
        self.route('PUT', ('setting',), self.setSetting)
        self.route('PUT', ('plugins',), self.enablePlugins)
        self.route('PUT', ('restart',), self.restartServer)
        self.route('GET', ('uploads',), self.getPartialUploads)
        self.route('DELETE', ('uploads',), self.discardPartialUploads)
        self.route('GET', ('check',), self.systemStatus)
        self.route('PUT', ('check',), self.systemConsistencyCheck)
        self.route('GET', ('log',), self.getLog)
        self.route('GET', ('log', 'level'), self.getLogLevel)
        self.route('PUT', ('log', 'level'), self.setLogLevel)
        self.route('POST', ('web_build',), self.buildWebCode)
        self.route('GET', ('setting', 'collection_creation_policy', 'access'),
                   self.getCollectionCreationPolicyAccess)

    @access.admin
    @autoDescribeRoute(
        Description('Set the value for a system setting, or a list of them.')
        .notes('Must be a system administrator to call this. If the value passed is '
               'a valid JSON object, it will be parsed and stored as an object.')
        .param('key', 'The key identifying this setting.', required=False)
        .param('value', 'The value for this setting.', required=False)
        .jsonParam('list', 'A JSON list of objects with key and value representing '
                   'a list of settings to set.', required=False, requireArray=True)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def setSetting(self, key, value, list):
        if list is None:
            list = ({'key': key, 'value': value},)

        for setting in list:
            key, value = setting['key'], setting['value']
            if isinstance(value, six.string_types):
                try:
                    value = json.loads(value)
                except ValueError:
                    pass

            if value is None:
                Setting().unset(key=key)
            else:
                Setting().set(key=key, value=value)

        return True

    @access.admin(scope=TokenScope.SETTINGS_READ)
    @autoDescribeRoute(
        Description('Get the value of a system configuration option.')
        .notes('Must be a system administrator to call this.')
        .param('section', 'The section identifying the configuration option.', required=True)
        .param('key', 'The key identifying the configuration option.', required=True)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('No such option with the given section/key exists.', 404)
    )
    def getConfigurationOption(self, section, key, params):
        configSection = config.getConfig().get(section)

        if configSection is None:
            raise ResourcePathNotFound('No section with that name exists.')
        elif key not in configSection:
            raise ResourcePathNotFound('No key with that name exists.')
        else:
            return configSection.get(key)

    @access.admin(scope=TokenScope.SETTINGS_READ)
    @autoDescribeRoute(
        Description('Get the value of a system setting, or a list of them.')
        .notes('Must be a system administrator to call this.')
        .param('key', 'The key identifying this setting.', required=False)
        .jsonParam('list', 'A JSON list of keys representing a set of settings to return.',
                   required=False, requireArray=True)
        .param('default', 'If "none", return a null value if a setting is '
               'currently the default value. If "default", return the '
               'default value of the setting(s).', required=False)
        .errorResponse('You are not a system administrator.', 403)
    )
    def getSetting(self, key, list, default):
        getFuncName = 'get'
        funcParams = {}
        if default is not None:
            if default == 'none':
                funcParams['default'] = None
            elif default == 'default':
                getFuncName = 'getDefault'
            elif default:
                raise RestException("Default was not 'none', 'default', or blank.")
        getFunc = getattr(Setting(), getFuncName)
        if list is not None:
            return {k: getFunc(k, **funcParams) for k in list}
        else:
            self.requireParams({'key': key})
            return getFunc(key, **funcParams)

    @access.admin(scope=TokenScope.PLUGINS_ENABLED_READ)
    @autoDescribeRoute(
        Description('Get the lists of all available and all enabled plugins.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getPlugins(self):
        plugins = {
            'all': plugin_utilities.findAllPlugins(),
            'enabled': Setting().get(SettingKey.PLUGINS_ENABLED)
        }
        failureInfo = plugin_utilities.getPluginFailureInfo()
        if failureInfo:
            plugins['failed'] = failureInfo
        return plugins

    @access.public
    @autoDescribeRoute(
        Description('Get the version information for this server.')
    )
    def getVersion(self):
        version = dict(**VERSION)
        version['apiVersion'] = API_VERSION
        version['serverStartDate'] = ModuleStartTime
        return version

    @access.admin
    @autoDescribeRoute(
        Description('Set the list of enabled plugins for the system.')
        .responseClass('Setting')
        .notes('Must be a system administrator to call this.')
        .jsonParam('plugins', 'JSON array of plugins to enable.', requireArray=True)
        .errorResponse('Required dependencies do not exist.', 500)
        .errorResponse('You are not a system administrator.', 403)
    )
    def enablePlugins(self, plugins):
        # Determine what plugins have been disabled and remove their associated routes.
        setting = Setting()
        routeTable = setting.get(SettingKey.ROUTE_TABLE)
        oldPlugins = setting.get(SettingKey.PLUGINS_ENABLED)
        reservedRoutes = {GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID}

        routeTableChanged = False
        removedRoutes = (
            set(oldPlugins) - set(plugins) - reservedRoutes)

        for route in removedRoutes:
            if route in routeTable:
                del routeTable[route]
                routeTableChanged = True

        if routeTableChanged:
            setting.set(SettingKey.ROUTE_TABLE, routeTable)

        # Route cleanup is done; update list of enabled plugins.
        return setting.set(SettingKey.PLUGINS_ENABLED, plugins)

    @access.admin
    @autoDescribeRoute(
        Description('Unset the value for a system setting.')
        .notes('Must be a system administrator to call this. This is used to '
               'explicitly restore a setting to its default value.')
        .param('key', 'The key identifying the setting to unset.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def unsetSetting(self, key):
        return Setting().unset(key)

    @access.admin(scope=TokenScope.PARTIAL_UPLOAD_READ)
    @autoDescribeRoute(
        Description('Get a list of uploads that have not been finished.')
        .notes('Must be a system administrator to call this.')
        .param('uploadId', 'List only a specific upload.', required=False)
        .param('userId', 'Restrict listing uploads to those started by a '
               'specific user.', required=False)
        .param('parentId', 'Restrict listing uploads to those within a '
               'specific folder or item.', required=False)
        .param('assetstoreId', 'Restrict listing uploads within a specific assetstore.',
               required=False)
        .param('minimumAge', 'Restrict listing uploads to those that are at '
               'least this many days old.', dataType='float', required=False)
        .param('includeUntracked', 'Some assetstores can have partial uploads '
               'that are no longer in the Girder database.  If this is True, '
               'include all of them (only filtered by assetstoreId) in the '
               'result list.', required=False, dataType='boolean', default=True)
        .pagingParams(defaultSort='updated')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getPartialUploads(self, uploadId, userId, parentId, assetstoreId, minimumAge,
                          includeUntracked, limit, offset, sort):
        filters = {}
        if uploadId is not None:
            filters['uploadId'] = uploadId
        if userId is not None:
            filters['userId'] = userId
        if assetstoreId is not None:
            filters['assetstoreId'] = assetstoreId
        if parentId is not None:
            filters['parentId'] = parentId
        if minimumAge is not None:
            filters['minimumAge'] = minimumAge

        uploadList = list(Upload().list(
            filters=filters, limit=limit, offset=offset, sort=sort))
        if includeUntracked and (limit == 0 or len(uploadList) < limit):
            untrackedList = Upload().untrackedUploads('list', assetstoreId)
            if limit == 0:
                uploadList += untrackedList
            elif len(uploadList) < limit:
                uploadList += untrackedList[:limit-len(uploadList)]
        return uploadList

    @access.admin(scope=TokenScope.PARTIAL_UPLOAD_CLEAN)
    @autoDescribeRoute(
        Description('Discard uploads that have not been finished.')
        .notes('Must be a system administrator to call this. This frees '
               'resources that were allocated for the uploads and clears the '
               'uploads from database.')
        .param('uploadId', 'Clear only a specific upload.', required=False)
        .param('userId', 'Restrict clearing uploads to those started by a '
               'specific user.', required=False)
        .param('parentId', 'Restrict clearing uploads to those within a '
               'specific folder or item.', required=False)
        .param('assetstoreId', 'Restrict clearing uploads within a specific assetstore.',
               required=False)
        .param('minimumAge', 'Restrict clearing uploads to those that are at '
               'least this many days old.', dataType='float', required=False)
        .param('includeUntracked', 'Some assetstores can have partial uploads '
               'that are no longer in the Girder database.  If this is True, '
               'remove all of them (only filtered by assetstoreId).',
               required=False, dataType='boolean', default=True)
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to delete upload', 500)
    )
    def discardPartialUploads(self, uploadId, userId, parentId, assetstoreId,
                              minimumAge, includeUntracked):
        filters = {}
        if uploadId is not None:
            filters['uploadId'] = uploadId
        if userId is not None:
            filters['userId'] = userId
        if assetstoreId is not None:
            filters['assetstoreId'] = assetstoreId
        if parentId is not None:
            filters['parentId'] = parentId
        if minimumAge is not None:
            filters['minimumAge'] = minimumAge
        uploadList = list(Upload().list(filters=filters))
        # Move the results to list that isn't a cursor so we don't have to have
        # the cursor sitting around while we work on the data.
        for upload in uploadList:
            try:
                Upload().cancelUpload(upload)
            except OSError as exc:
                if exc.errno == errno.EACCES:
                    raise GirderException(
                        'Failed to delete upload.',
                        'girder.api.v1.system.delete-upload-failed')
                raise
        if includeUntracked:
            uploadList += Upload().untrackedUploads('delete', assetstoreId)
        return uploadList

    @access.admin
    @autoDescribeRoute(
        Description('Restart the Girder REST server.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def restartServer(self):
        if not config.getConfig()['server'].get('cherrypy_server', True):
            raise RestException('Restarting of server is disabled.', 403)

        class Restart(cherrypy.process.plugins.Monitor):
            def __init__(self, bus, frequency=1):
                cherrypy.process.plugins.Monitor.__init__(
                    self, bus, self.run, frequency)

            def start(self):
                cherrypy.process.plugins.Monitor.start(self)

            def run(self):
                self.bus.log('Restarting.')
                self.thread.cancel()
                self.bus.restart()

        restart = Restart(cherrypy.engine)
        restart.subscribe()
        restart.start()
        return {
            'restarted': datetime.datetime.utcnow()
        }

    @access.public
    @autoDescribeRoute(
        Description('Report the current system status.')
        .notes('Must be a system administrator to call this with any mode '
               'other than basic.')
        .param('mode', 'Select details to return. "quick" are the details '
               'that can be answered without much load on the system. "slow" '
               'also includes some resource-intensive queries.',
               required=False, enum=('basic', 'quick', 'slow'), default='basic')
        .errorResponse('You are not a system administrator.', 403)
    )
    def systemStatus(self, mode):
        user = self.getCurrentUser()
        if mode != 'basic':
            self.requireAdmin(user)
        status = system.getStatus(mode, user)
        status['requestBase'] = cherrypy.request.base.rstrip('/')
        return status

    @access.public
    @autoDescribeRoute(Description('List all access flags available in the system.'))
    def getAccessFlags(self):
        return ACCESS_FLAGS

    @access.admin
    @autoDescribeRoute(
        Description('Perform a variety of system checks to verify that all is '
                    'well.')
        .notes('Must be a system administrator to call this.  This verifies '
               'and corrects some issues, such as incorrect folder sizes.')
        .param('progress', 'Whether to record progress on this task.',
               required=False, dataType='boolean', default=False)
        .errorResponse('You are not a system administrator.', 403)
    )
    def systemConsistencyCheck(self, progress):
        user = self.getCurrentUser()
        title = 'Running system consistency check'
        with ProgressContext(progress, user=user, title=title) as pc:
            results = {}
            pc.update(title='Checking for orphaned records (Step 1 of 3)')
            results['orphansRemoved'] = self._pruneOrphans(pc)
            pc.update(title='Checking for incorrect base parents (Step 2 of 3)')
            results['baseParentsFixed'] = self._fixBaseParents(pc)
            pc.update(title='Checking for incorrect sizes (Step 3 of 3)')
            results['sizesChanged'] = self._recalculateSizes(pc)
            return results
        # TODO:
        # * check that all files are associated with an existing item
        # * check that all files exist within their assetstore and are the
        #   expected size
        # * check that all folders have a valid ancestor tree leading to a
        #   user or collection
        # * check that all folders have the correct baseParentId and
        #   baseParentType
        # * check that all groups contain valid users
        # * check that all resources validate
        # * for filesystem assetstores, find files that are not tracked.
        # * for gridfs assetstores, find chunks that are not tracked.
        # * for s3 assetstores, find elements that are not tracked.

    @access.admin
    @autoDescribeRoute(
        Description('Show the most recent contents of the server logs.')
        .notes('Must be a system administrator to call this.')
        .param('bytes', 'Controls how many bytes (from the end of the log) to show. '
               'Pass 0 to show the whole log.', dataType='integer', required=False, default=4096)
        .param('log', 'Which log to tail.', enum=('error', 'info'),
               required=False, default='error')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getLog(self, bytes, log):
        path = girder.getLogPaths()[log]
        filesize = os.path.getsize(path)
        length = int(bytes) or filesize
        filesize1 = 0
        if length > filesize:
            path1 = path + '.1'
            if os.path.exists(path1):
                filesize1 = os.path.getsize(path1)

        def stream():
            yield '=== Last %d bytes of %s: ===\n\n' % (
                min(length, filesize + filesize1), path
            )

            readlength = length
            if readlength > filesize and filesize1:
                readlength = length - filesize
                with open(path1, 'rb') as f:
                    if readlength < filesize1:
                        f.seek(-readlength, os.SEEK_END)
                    while True:
                        data = f.read(LOG_BUF_SIZE)
                        if not data:
                            break
                        yield data
                readlength = filesize
            with open(path, 'rb') as f:
                if readlength < filesize:
                    f.seek(-readlength, os.SEEK_END)
                while True:
                    data = f.read(LOG_BUF_SIZE)
                    if not data:
                        break
                    yield data
        return stream

    @access.admin
    @autoDescribeRoute(
        Description('Get the current log level.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getLogLevel(self):
        level = girder.logger.getEffectiveLevel()
        return logging.getLevelName(level)

    @access.admin
    @autoDescribeRoute(
        Description('Get the current log level.')
        .notes('Must be a system administrator to call this.')
        .param('level', 'The new level to set.',
               enum=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
               default='INFO')
        .errorResponse('You are not a system administrator.', 403)
    )
    def setLogLevel(self, level):
        level = logging.getLevelName(level)
        for logger in (girder.logger, cherrypy.log.access_log, cherrypy.log.error_log):
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
        return logging.getLevelName(level)

    @access.admin
    @autoDescribeRoute(
        Description('Rebuild web client code.')
        .param('progress', 'Whether to record progress on this task.', required=False,
               dataType='boolean', default=False)
        .param('dev', 'Whether to build for development mode.', required=False,
               dataType='boolean', default=False)
    )
    def buildWebCode(self, progress, dev):
        user = self.getCurrentUser()

        with ProgressContext(progress, user=user, title='Building web client code') as progress:
            install.runWebBuild(dev=dev, progress=progress)

    @access.admin
    @autoDescribeRoute(
        Description('Get access of content creation policy.')
        .notes('Get result in the same structure as the access endpoints'
               'of collection, file, and group')
    )
    def getCollectionCreationPolicyAccess(self):
        cpp = Setting().get('core.collection_create_policy')

        acList = {
            'users': [{'id': x} for x in cpp.get('users', [])],
            'groups': [{'id': x} for x in cpp.get('groups', [])]
        }

        for user in acList['users'][:]:
            userDoc = User().load(
                user['id'], force=True,
                fields=['firstName', 'lastName', 'login'])
            if userDoc is None:
                acList['users'].remove(user)
            else:
                user['login'] = userDoc['login']
                user['name'] = ' '.join((userDoc['firstName'], userDoc['lastName']))

        for grp in acList['groups'][:]:
            grpDoc = Group().load(
                grp['id'], force=True, fields=['name', 'description'])
            if grpDoc is None:
                acList['groups'].remove(grp)
            else:
                grp['name'] = grpDoc['name']
                grp['description'] = grpDoc['description']

        return acList

    def _fixBaseParents(self, progress):
        fixes = 0
        models = ['folder', 'item']
        steps = sum(self.model(model).find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in self.model(model).find():
                progress.update(increment=1)
                baseParent = self.model(model).parentsToRoot(doc, force=True)[0]
                baseParentType = baseParent['type']
                baseParentId = baseParent['object']['_id']
                if (doc['baseParentType'] != baseParentType or
                        doc['baseParentId'] != baseParentId):
                    self.model(model).update({'_id': doc['_id']}, update={
                        '$set': {
                            'baseParentType': baseParentType,
                            'baseParentId': baseParentId
                        }})
                    fixes += 1
        return fixes

    def _pruneOrphans(self, progress):
        count = 0
        models = ['folder', 'item', 'file']
        steps = sum(self.model(model).find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in self.model(model).find():
                progress.update(increment=1)
                if self.model(model).isOrphan(doc):
                    self.model(model).remove(doc)
                    count += 1
        return count

    def _recalculateSizes(self, progress):
        fixes = 0
        models = ['collection', 'user']
        steps = sum(self.model(model).find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in self.model(model).find():
                progress.update(increment=1)
                _, f = self.model(model).updateSize(doc)
                fixes += f
        return fixes
