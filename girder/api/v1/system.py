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
import json

from girder.api import access
from girder.constants import SettingKey, VERSION
from girder.models.model_base import GirderException
from girder.utility import plugin_utilities
from girder.utility import system
from girder.utility.progress import ProgressContext
from ..describe import API_VERSION, Description
from ..rest import Resource, RestException

ModuleStartTime = datetime.datetime.utcnow()


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """
    def __init__(self):
        self.resourceName = 'system'
        self.route('DELETE', ('setting',), self.unsetSetting)
        self.route('GET', ('version',), self.getVersion)
        self.route('GET', ('setting',), self.getSetting)
        self.route('GET', ('plugins',), self.getPlugins)
        self.route('PUT', ('setting',), self.setSetting)
        self.route('PUT', ('plugins',), self.enablePlugins)
        self.route('PUT', ('restart',), self.restartServer)
        self.route('GET', ('uploads',), self.getPartialUploads)
        self.route('DELETE', ('uploads',), self.discardPartialUploads)
        self.route('GET', ('check',), self.systemStatus)
        self.route('PUT', ('check',), self.systemConsistencyCheck)

    @access.admin
    def setSetting(self, params):
        """
        Set a system-wide setting. Validation of the setting is performed in
        the setting model. If the setting is a valid JSON string, it will be
        passed to the model as the corresponding dict, otherwise it is simply
        passed as a raw string.
        """
        if 'list' in params:
            try:
                settings = json.loads(params['list'])

                if type(settings) is not list:
                    raise ValueError()
            except ValueError:
                raise RestException('List was not a valid JSON list.')
        else:
            self.requireParams(('key', 'value'), params)
            settings = ({'key': params['key'], 'value': params['value']},)

        for setting in settings:
            if setting['value'] is None:
                value = None
            else:
                try:
                    if isinstance(setting['value'], basestring):
                        value = json.loads(setting['value'])
                    else:
                        value = setting['value']
                except ValueError:
                    value = setting['value']

            if value is None:
                self.model('setting').unset(key=setting['key'])
            else:
                self.model('setting').set(key=setting['key'], value=value)

        return True
    setSetting.description = (
        Description('Set the value for a system setting, or a list of them.')
        .notes("""Must be a system administrator to call this. If the value
               passed is a valid JSON object, it will be parsed and stored
               as an object.""")
        .param('key', 'The key identifying this setting.', required=False)
        .param('value', 'The value for this setting.', required=False)
        .param('list', 'A JSON list of objects with key and value representing '
               'a list of settings to set.', required=False)
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def getSetting(self, params):
        getFuncName = 'get'
        funcParams = {}
        if 'default' in params:
            if params['default'] == 'none':
                funcParams['default'] = None
            elif params['default'] == 'default':
                getFuncName = 'getDefault'
            elif len(params['default']):
                raise RestException("Default was not 'none', 'default', or "
                                    "blank.")
        getFunc = getattr(self.model('setting'), getFuncName)
        if 'list' in params:
            try:
                keys = json.loads(params['list'])

                if type(keys) is not list:
                    raise ValueError()
            except ValueError:
                raise RestException('List was not a valid JSON list.')

            return {k: getFunc(k, **funcParams) for k in keys}
        else:
            self.requireParams('key', params)
            return getFunc(params['key'], **funcParams)
    getSetting.description = (
        Description('Get the value of a system setting, or a list of them.')
        .notes('Must be a system administrator to call this.')
        .param('key', 'The key identifying this setting.', required=False)
        .param('list', 'A JSON list of keys representing a set of settings to'
               ' return.', required=False)
        .param('default', 'If "none", return a null value if a setting is '
               'currently the default value.  If "default", return the '
               'default value of the setting(s).', required=False)
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def getPlugins(self, params):
        """
        Return the plugin information for the system. This includes a list of
        all of the currently enabled plugins, as well as
        """
        return {
            'all': plugin_utilities.findAllPlugins(),
            'enabled': self.model('setting').get(SettingKey.PLUGINS_ENABLED)
        }
    getPlugins.description = (
        Description('Get the lists of all available and all enabled plugins.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403))

    @access.public
    def getVersion(self, params):
        version = dict(**VERSION)
        version['apiVersion'] = API_VERSION
        version['serverStartDate'] = ModuleStartTime
        return version
    getVersion.description = Description(
        'Get the version information for this server.')

    @access.admin
    def enablePlugins(self, params):
        self.requireParams('plugins', params)
        try:
            plugins = json.loads(params['plugins'])
        except ValueError:
            raise RestException('Plugins parameter should be a JSON list.')

        return self.model('setting').set(SettingKey.PLUGINS_ENABLED, plugins)
    enablePlugins.description = (
        Description('Set the list of enabled plugins for the system.')
        .responseClass('Setting')
        .notes('Must be a system administrator to call this.')
        .param('plugins', 'JSON array of plugins to enable.')
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def unsetSetting(self, params):
        self.requireParams('key', params)
        return self.model('setting').unset(params['key'])
    unsetSetting.description = (
        Description('Unset the value for a system setting.')
        .notes("""Must be a system administrator to call this. This is used to
               explicitly restore a setting to its default value.""")
        .param('key', 'The key identifying the setting to unset.')
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def getPartialUploads(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'updated')
        uploadList = list(self.model('upload').list(
            filters=params, limit=limit, offset=offset, sort=sort))
        untracked = self.boolParam('includeUntracked', params, default=True)
        if untracked and (limit == 0 or len(uploadList) < limit):
            assetstoreId = params.get('assetstoreId', None)
            untrackedList = self.model('upload').untrackedUploads('list',
                                                                  assetstoreId)
            if limit == 0:
                uploadList += untrackedList
            elif len(uploadList) < limit:
                uploadList += untrackedList[:limit-len(uploadList)]
        return uploadList
    getPartialUploads.description = (
        Description('Get a list of uploads that have not been finished.')
        .notes("Must be a system administrator to call this.")
        .param('uploadId', 'List only a specific upload.', required=False)
        .param('userId', 'Restrict listing uploads to those started by a '
               'specific user.', required=False)
        .param('parentId', 'Restrict listing uploads to those within a '
               'specific folder or item.', required=False)
        .param('assetstoreId', 'Restrict listing uploads within a specific '
               'assetstore.', required=False)
        .param('minimumAge', 'Restrict listing uploads to those that are at '
               'least this many days old.', required=False)
        .param('includeUntracked', 'Some assetstores can have partial uploads '
               'that are no longer in the Girder database.  If this is True, '
               'include all of them (only filtered by assetstoreId) in the '
               'result list.  Default True.',
               required=False, dataType='boolean')
        .param('limit', "Result set size limit (default=50).", required=False,
               dataType='int')
        .param('offset', "Offset into result set (default=0).", required=False,
               dataType='int')
        .param('sort', "Field to sort the upload list by (default=age)",
               required=False)
        .param('sortdir', "1 for ascending, -1 for descending (default=1)",
               required=False, dataType='int')
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def discardPartialUploads(self, params):
        uploadList = list(self.model('upload').list(filters=params))
        # Move the results to list that isn't a cursor so we don't have to have
        # the cursor sitting around while we work on the data.
        for upload in uploadList:
            try:
                self.model('upload').cancelUpload(upload)
            except OSError as exc:
                if exc[0] in (errno.EACCES,):
                    raise GirderException(
                        'Failed to delete upload.',
                        'girder.api.v1.system.delete-upload-failed')
                raise
        untracked = self.boolParam('includeUntracked', params, default=True)
        if untracked:
            assetstoreId = params.get('assetstoreId', None)
            uploadList += self.model('upload').untrackedUploads('delete',
                                                                assetstoreId)
        return uploadList
    discardPartialUploads.description = (
        Description('Discard uploads that have not been finished.')
        .notes("""Must be a system administrator to call this. This frees
               resources that were allocated for the uploads and clears the
               uploads from database.""")
        .param('uploadId', 'Clear only a specific upload.', required=False)
        .param('userId', 'Restrict clearing uploads to those started by a '
               'specific user.', required=False)
        .param('parentId', 'Restrict clearing uploads to those within a '
               'specific folder or item.', required=False)
        .param('assetstoreId', 'Restrict clearing uploads within a specific '
               'assetstore.', required=False)
        .param('minimumAge', 'Restrict clearing uploads to those that are at '
               'least this many days old.', required=False)
        .param('includeUntracked', 'Some assetstores can have partial uploads '
               'that are no longer in the Girder database.  If this is True, '
               'remove all of them (only filtered by assetstoreId).  Default '
               'True.',
               required=False, dataType='boolean')
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to delete upload', 500))

    @access.admin
    def restartServer(self, params):
        """
        Restart the girder rest server.  This reloads everything, which is
        currently necessary to enable or disable a plugin.
        """
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
    restartServer.description = (
        Description('Restart the Girder REST server.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403))

    @access.public
    def systemStatus(self, params):
        mode = params.get('mode', 'basic')
        user = self.getCurrentUser()
        if mode != 'basic':
            self.requireAdmin(user)
        status = system.getStatus(mode, user)
        status["requestBase"] = cherrypy.request.base.rstrip('/')
        return status
    systemStatus.description = (
        Description('Report the current system status.')
        .notes('Must be a system administrator to call this with any mode '
               'other than basic.')
        .param('mode', 'Select details to return.  "quick" are the details '
               'that can be answered without much load on the system.  "slow" '
               'also includes some resource-intensive queries.',
               required=False, enum=['basic', 'quick', 'slow'])
        .errorResponse('You are not a system administrator.', 403))

    @access.admin
    def systemConsistencyCheck(self, params):
        results = {}
        progress = self.boolParam('progress', params, default=False)
        models = ('item', )
        steps = 0
        if progress:
            for model in models:
                count, changed = self.model(model).checkConsistency(
                    stage='count')
                steps += count
        with ProgressContext(progress, user=self.getCurrentUser(),
                             title='Checking system', total=steps,
                             message='Checking system...') as ctx:
            for model in models:
                count, removed = self.model(model).checkConsistency(
                    stage='remove', progress=ctx)
                if removed:
                    results[model+'Removed'] = removed
            revmodels = list(models)
            revmodels.reverse()
            for model in revmodels:
                count, corrected = self.model(model).checkConsistency(
                    stage='verify', progress=ctx)
                if count:
                    results[model+'Count'] = count
                if corrected:
                    results[model+'Corrected'] = corrected
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
        return results
    systemConsistencyCheck.description = (
        Description('Perform a variety of system checks to verify that all is '
                    'well.')
        .notes("""Must be a system administrator to call this.  This verifies
               and corrects some issues, such as incorrect folder sizes.""")
        .param('progress', 'Whether to record progress on this task. Default '
               'is false.', required=False, dataType='boolean')
        .errorResponse('You are not a system administrator.', 403))
