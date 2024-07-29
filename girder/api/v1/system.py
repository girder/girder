import cherrypy
import datetime
import errno
from functools import lru_cache
from itertools import chain
import json
import logging

from girder import plugin
from girder.api import access
from girder.constants import TokenScope, ACCESS_FLAGS, VERSION
from girder.exceptions import GirderException, ResourcePathNotFound
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.plugin import getPluginStaticContent
from girder.settings import SettingKey
from girder.utility import config, system
from girder.utility.progress import ProgressContext
from ..describe import Description, autoDescribeRoute
from ..rest import Resource

ModuleStartTime = datetime.datetime.now(datetime.timezone.utc)
LOG_BUF_SIZE = 65536
logger = logging.getLogger(__name__)


class System(Resource):
    """
    The system endpoints are for querying and managing system-wide properties.
    """

    def __init__(self):
        super().__init__()
        self.resourceName = 'system'
        self.route('DELETE', ('setting',), self.unsetSetting)
        self.route('GET', ('version',), self.getVersion)
        self.route('GET', ('configuration',), self.getConfigurationOption)
        self.route('GET', ('setting',), self.getSetting)
        self.route('GET', ('public_settings',), self.getPublicSettings)
        self.route('GET', ('plugins',), self.getPlugins)
        self.route('GET', ('plugin_static_files',), self.getPluginStaticFiles)
        self.route('GET', ('access_flag',), self.getAccessFlags)
        self.route('PUT', ('setting',), self.setSetting)
        self.route('GET', ('uploads',), self.getPartialUploads)
        self.route('DELETE', ('uploads',), self.discardPartialUploads)
        self.route('GET', ('check',), self.systemStatus)
        self.route('PUT', ('check',), self.systemConsistencyCheck)
        self.route('GET', ('setting', 'collection_creation_policy', 'access'),
                   self.getCollectionCreationPolicyAccess)

    @access.public
    @autoDescribeRoute(
        Description('Get the list of plugin static files to be injected into the Girder app.'),
        hide=True,
    )
    @lru_cache(maxsize=1)  # this serves data that is immutable after server startup
    def getPluginStaticFiles(self):
        contentObjects = list(getPluginStaticContent().values())
        return {
            'css': list(chain(*[content.css for content in contentObjects])),
            'js': list(chain(*[content.js for content in contentObjects])),
        }

    @access.admin
    @autoDescribeRoute(
        Description('Set the value for a system setting, or a list of them.')
        .notes('Must be a system administrator to call this. If the value passed is '
               'a valid JSON object, it will be parsed and stored as an object.')
        .param('key', 'The key identifying this setting.', required=False, paramType='formData')
        .param('value', 'The value for this setting.', required=False, paramType='formData')
        .jsonParam('list', 'A JSON list of objects with key and value representing '
                   'a list of settings to set.', required=False, requireArray=True,
                   paramType='formData')
        .errorResponse('You are not a system administrator.', 403)
        .errorResponse('Failed to set system setting.', 500)
    )
    def setSetting(self, key, value, list):
        if list is None:
            list = ({'key': key, 'value': value},)

        for setting in list:
            key, value = setting['key'], setting['value']
            if isinstance(value, str):
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
        .errorResponse('You are not a system administrator.', 403)
    )
    def getSetting(self, key, list):
        if list is not None:
            return {k: Setting().get(k) for k in list}
        else:
            self.requireParams({'key': key})
            return Setting().get(key)

    @access.public()
    @autoDescribeRoute(
        Description('Get publicly accessible settings.')
    )
    def getPublicSettings(self):
        publicSettings = [
            SettingKey.BRAND_NAME,
            SettingKey.CONTACT_EMAIL_ADDRESS,
            SettingKey.PRIVACY_NOTICE,
            SettingKey.BANNER_COLOR,
            SettingKey.REGISTRATION_POLICY,
            SettingKey.ENABLE_PASSWORD_LOGIN,
        ]
        return {k: Setting().get(k) for k in publicSettings}

    @access.admin(scope=TokenScope.PLUGINS_READ)
    @autoDescribeRoute(
        Description('Get the lists of all available and all loaded plugins.')
        .notes('Must be a system administrator to call this.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getPlugins(self):
        def _pluginNameToResponse(name):
            p = plugin.getPlugin(name)
            return {
                'name': p.displayName,
                'description': p.description,
                'url': p.url,
                'version': p.version
            }

        return {
            'all': {name: _pluginNameToResponse(name) for name in plugin.allPlugins()},
            'loaded': plugin.loadedPlugins()
        }

    @access.public
    @autoDescribeRoute(
        Description('Get the version information for this server.')
    )
    def getVersion(self):
        version = dict(**VERSION)
        version['serverStartDate'] = ModuleStartTime
        return version

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
            try:
                untrackedList = Upload().untrackedUploads('list', assetstoreId)
                if limit == 0:
                    uploadList += untrackedList
                elif len(uploadList) < limit:
                    uploadList += untrackedList[:limit - len(uploadList)]
            except Exception:
                logger.debug('Could not get untracked uploads for assetstore %s', assetstoreId)
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
            try:
                uploadList += Upload().untrackedUploads('delete', assetstoreId)
            except Exception:
                logger.debug('Could not delete untracked uploads for assetstore %s', assetstoreId)
        return uploadList

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
        # * for s3 assetstores, find elements that are not tracked.

    @access.admin
    @autoDescribeRoute(
        Description('Get access of content creation policy.')
        .notes('Get result in the same structure as the access endpoints '
               'of collection, file, and group')
    )
    def getCollectionCreationPolicyAccess(self):
        cpp = Setting().get(SettingKey.COLLECTION_CREATE_POLICY)

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
        models = [Folder(), Item()]
        steps = sum(model.find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in model.find():
                progress.update(increment=1)
                baseParent = model.parentsToRoot(doc, force=True)[0]
                baseParentType = baseParent['type']
                baseParentId = baseParent['object']['_id']
                if (doc['baseParentType'] != baseParentType or doc['baseParentId'] != baseParentId):
                    model.update({'_id': doc['_id']}, update={
                        '$set': {
                            'baseParentType': baseParentType,
                            'baseParentId': baseParentId
                        }})
                    fixes += 1
        return fixes

    def _pruneOrphans(self, progress):
        count = 0
        models = [File(), Folder(), Item()]
        steps = sum(model.find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in model.find():
                progress.update(increment=1)
                if model.isOrphan(doc):
                    model.remove(doc)
                    count += 1
        return count

    def _recalculateSizes(self, progress):
        fixes = 0
        models = [Collection(), User()]
        steps = sum(model.find().count() for model in models)
        progress.update(total=steps, current=0)
        for model in models:
            for doc in model.find():
                progress.update(increment=1)
                _, f = model.updateSize(doc)
                fixes += f
        return fixes
