# -*- coding: utf-8 -*-
import json
import os
import time
import unittest.mock

from .. import base
from girder.api import access
from girder.api.describe import describeRoute
from girder.api.rest import getApiUrl, loadmodel, Resource
from girder.constants import AccessType, registerAccessFlag, ROOT_DIR, VERSION
from girder.exceptions import AccessException, ValidationException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingDefault, SettingKey
from girder.utility import config


class TestEndpoints(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'test_endpoints'

        self.route('GET', ('loadmodel_with_flags', ':id'), self.loadModelFlags)

    @access.public
    @describeRoute(None)
    @loadmodel(model='user', level=AccessType.READ, requiredFlags='my_key')
    def loadModelFlags(self, user, params):
        return 'success'


def setUpModule():
    testServer = base.startServer()
    testServer.root.api.v1.test_endpoints = TestEndpoints()


def tearDownModule():
    base.stopServer()


class SystemTestCase(base.TestCase):
    """
    Contains tests of the /system API endpoints.
    """

    def setUp(self):
        super().setUp()

        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder.test' % num)
            for num in [0, 1]]

        self.group = Group().createGroup('test group', creator=self.users[1])

    def tearDown(self):
        # Restore the state of the plugins configuration
        conf = config.getConfig()
        if 'plugins' in conf:
            del conf['plugins']

    def testGetVersion(self):
        resp = self.request(path='/system/version', method='GET')
        self.assertEqual(resp.json['release'], VERSION['release'])

    def testSettings(self):
        users = self.users

        # Only admins should be able to get or set settings
        for method in ('GET', 'PUT', 'DELETE'):
            resp = self.request(path='/system/setting', method=method, params={
                'key': 'foo',
                'value': 'bar'
            }, user=users[1])
            self.assertStatus(resp, 403)

        # Only valid setting keys should be allowed
        resp = self.request(path='/system/setting', method='PUT', params={
            'key': 'foo',
            'value': 'bar'
        }, user=users[0])
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['field'], 'key')

        # Only a valid JSON list is permitted
        resp = self.request(path='/system/setting', method='GET', params={
            'list': json.dumps('not_a_list')
        }, user=users[0])
        self.assertStatus(resp, 400)

        resp = self.request(path='/system/setting', method='PUT', params={
            'list': json.dumps('not_a_list')
        }, user=users[0])
        self.assertStatus(resp, 400)

        # Set an invalid setting value, should fail
        resp = self.request(path='/system/setting', method='PUT', params={
            'key': SettingKey.BANNER_COLOR,
            'value': 'bar'
        }, user=users[0])
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'The banner color must be a hex color triplet')

        # Set a valid value
        resp = self.request(path='/system/setting', method='PUT', params={
            'key': SettingKey.BANNER_COLOR,
            'value': '#121212'
        }, user=users[0])
        self.assertStatusOk(resp)

        # We should now be able to retrieve it
        resp = self.request(path='/system/setting', method='GET', params={
            'key': SettingKey.BANNER_COLOR
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, '#121212')

        # We should now clear the setting
        resp = self.request(path='/system/setting', method='DELETE', params={
            'key': SettingKey.BANNER_COLOR
        }, user=users[0])
        self.assertStatusOk(resp)

        # Setting should now be default
        setting = Setting().get(SettingKey.BANNER_COLOR)
        self.assertEqual(setting, SettingDefault.defaults[SettingKey.BANNER_COLOR])

        # We should also be able to put several setting using a JSON list
        resp = self.request(path='/system/setting', method='PUT', params={
            'list': json.dumps([
                {'key': SettingKey.BANNER_COLOR, 'value': '#121212'},
                {'key': SettingKey.COOKIE_LIFETIME, 'value': None},
            ])
        }, user=users[0])
        self.assertStatusOk(resp)

        # We can get a list as well
        resp = self.request(path='/system/setting', method='GET', params={
            'list': json.dumps([
                SettingKey.BANNER_COLOR,
                SettingKey.COOKIE_LIFETIME,
            ])
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[SettingKey.BANNER_COLOR], '#121212')

        # Try to set each key in turn to test the validation.  First test with
        # am invalid value, then test with the default value.  If the value
        # 'bad' won't trigger a validation error, the key should be present in
        # the badValues table.
        badValues = {
            SettingKey.BRAND_NAME: '',
            SettingKey.BANNER_COLOR: '',
            SettingKey.EMAIL_FROM_ADDRESS: '',
            SettingKey.PRIVACY_NOTICE: '',
            SettingKey.CONTACT_EMAIL_ADDRESS: '',
            SettingKey.EMAIL_HOST: {},
            SettingKey.SMTP_HOST: '',
            SettingKey.SMTP_PASSWORD: {},
            SettingKey.SMTP_USERNAME: {},
            SettingKey.CORS_ALLOW_ORIGIN: {},
            SettingKey.CORS_ALLOW_METHODS: {},
            SettingKey.CORS_ALLOW_HEADERS: {},
            SettingKey.CORS_EXPOSE_HEADERS: {},
        }
        allKeys = dict.fromkeys(SettingDefault.defaults.keys())
        allKeys.update(badValues)
        for key in allKeys:
            resp = self.request(path='/system/setting', method='PUT', params={
                'key': key,
                'value': badValues.get(key, 'bad')
            }, user=users[0])
            self.assertStatus(resp, 400)
            resp = self.request(path='/system/setting', method='PUT', params={
                'key': key,
                'value': json.dumps(SettingDefault.defaults.get(key, ''))
            }, user=users[0])
            self.assertStatusOk(resp)
            resp = self.request(path='/system/setting', method='PUT', params={
                'list': json.dumps([{'key': key, 'value': None}])
            }, user=users[0])
            self.assertStatusOk(resp)

    def testCheck(self):
        resp = self.request(path='/token/session', method='GET')
        self.assertStatusOk(resp)
        token = resp.json['token']
        # 'basic' mode should work for a token or for anonymous
        resp = self.request(path='/system/check', token=token)
        self.assertStatusOk(resp)
        check = resp.json
        self.assertLess(check['bootTime'], time.time())
        resp = self.request(path='/system/check')
        self.assertStatusOk(resp)
        check = resp.json
        self.assertLess(check['bootTime'], time.time())
        # but should fail for 'quick' mode
        resp = self.request(path='/system/check', token=token, params={
            'mode': 'quick'})
        self.assertStatus(resp, 401)
        # Admin can ask for any mode
        resp = self.request(path='/system/check', user=self.users[0])
        self.assertStatusOk(resp)
        check = resp.json
        self.assertLess(check['bootTime'], time.time())
        self.assertNotIn('cherrypyThreadsInUse', check)
        resp = self.request(path='/system/check', user=self.users[0], params={
            'mode': 'quick'})
        self.assertStatusOk(resp)
        check = resp.json
        self.assertLess(check['bootTime'], time.time())
        self.assertGreaterEqual(check['cherrypyThreadsInUse'], 1)
        self.assertIn('rss', check['processMemory'])
        resp = self.request(path='/system/check', user=self.users[0], params={
            'mode': 'slow'})
        self.assertStatusOk(resp)
        check = resp.json
        self.assertGreater(check['girderDiskUsage']['free'], 0)
        resp = self.request(path='/system/check', method='PUT',
                            user=self.users[0], params={'progress': True})
        self.assertStatusOk(resp)
        # tests that check repair of different models are convered in the
        # individual models' tests

    def testConsistencyCheck(self):
        user = self.users[0]
        c1 = Collection().createCollection('c1', user)
        f1 = Folder().createFolder(c1, 'f1', parentType='collection')
        Folder().createFolder(c1, 'f2', parentType='collection')
        f3 = Folder().createFolder(user, 'f3', parentType='user')
        Folder().createFolder(user, 'f4', parentType='user')
        i1 = Item().createItem('i1', user, f1)
        i2 = Item().createItem('i2', user, f1)
        Item().createItem('i3', user, f1)
        i4 = Item().createItem('i4', user, f3)
        Item().createItem('i5', user, f3)
        Item().createItem('i6', user, f3)
        assetstore = {'_id': 0}
        File().createFile(user, i1, 'foo', 7, assetstore)
        File().createFile(user, i1, 'foo', 13, assetstore)
        File().createFile(user, i2, 'foo', 19, assetstore)
        File().createFile(user, i4, 'foo', 23, assetstore)

        self.assertEqual(39, Collection().load(c1['_id'], force=True)['size'])
        self.assertEqual(39, Folder().load(f1['_id'], force=True)['size'])
        self.assertEqual(23, Folder().load(f3['_id'], force=True)['size'])
        self.assertEqual(20, Item().load(i1['_id'], force=True)['size'])
        self.assertEqual(23, User().load(user['_id'], force=True)['size'])

        resp = self.request(path='/system/check', user=user, method='PUT')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['baseParentsFixed'], 0)
        self.assertEqual(resp.json['orphansRemoved'], 0)
        self.assertEqual(resp.json['sizesChanged'], 0)

        Item().update({'_id': i1['_id']}, update={'$set': {'baseParentId': None}})

        resp = self.request(path='/system/check', user=user, method='PUT')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['baseParentsFixed'], 1)
        self.assertEqual(resp.json['orphansRemoved'], 0)
        self.assertEqual(resp.json['sizesChanged'], 0)

        Collection().update({'_id': c1['_id']}, update={'$set': {'size': 0}})
        Folder().update({'_id': f1['_id']}, update={'$set': {'size': 0}})
        Item().update({'_id': i1['_id']}, update={'$set': {'size': 0}})

        resp = self.request(path='/system/check', user=user, method='PUT')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['baseParentsFixed'], 0)
        self.assertEqual(resp.json['orphansRemoved'], 0)
        self.assertEqual(resp.json['sizesChanged'], 3)

        self.assertEqual(39, Collection().load(c1['_id'], force=True)['size'])
        self.assertEqual(39, Folder().load(f1['_id'], force=True)['size'])
        self.assertEqual(23, Folder().load(f3['_id'], force=True)['size'])
        self.assertEqual(20, Item().load(i1['_id'], force=True)['size'])
        self.assertEqual(23, User().load(user['_id'], force=True)['size'])

        Folder().collection.delete_one({'_id': f3['_id']})

        resp = self.request(path='/system/check', user=user, method='PUT')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['baseParentsFixed'], 0)
        self.assertEqual(resp.json['orphansRemoved'], 3)
        self.assertEqual(resp.json['sizesChanged'], 0)

        self.assertEqual(
            0, User().load(user['_id'], force=True)['size'])

    def testLogRoute(self):
        logRoot = os.path.join(ROOT_DIR, 'tests', 'cases', 'dummylogs')
        config.getConfig()['logging'] = {'log_root': logRoot}

        resp = self.request(path='/system/log', user=self.users[1], params={
            'log': 'error',
            'bytes': 0
        })
        self.assertStatus(resp, 403)

        resp = self.request(path='/system/log', user=self.users[0], params={
            'log': 'error',
            'bytes': 0
        }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(
            self.getBody(resp),
            '=== Last 12 bytes of %s/error.log: ===\n\nHello world\n' % logRoot)

        resp = self.request(path='/system/log', user=self.users[0], params={
            'log': 'error',
            'bytes': 6
        }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(
            self.getBody(resp),
            '=== Last 6 bytes of %s/error.log: ===\n\nworld\n' % logRoot)

        resp = self.request(path='/system/log', user=self.users[0], params={
            'log': 'error',
            'bytes': 18
        }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(
            self.getBody(resp),
            '=== Last 18 bytes of %s/error.log: ===\n\nmonde\nHello world\n' % logRoot)

        resp = self.request(path='/system/log', user=self.users[0], params={
            'log': 'info',
            'bytes': 6
        }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(
            self.getBody(resp),
            '=== Last 0 bytes of %s/info.log: ===\n\n' % logRoot)

        del config.getConfig()['logging']

    def testLogLevel(self):
        from girder import logger, _attachFileLogHandlers
        _attachFileLogHandlers()
        for handler in logger.handlers:
            if handler._girderLogHandler == 'info':
                handler.emit = unittest.mock.MagicMock()
                infoEmit = handler.emit
            elif handler._girderLogHandler == 'error':
                handler.emit = unittest.mock.MagicMock()
                errorEmit = handler.emit
        # We should be an info level
        resp = self.request(path='/system/log/level', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 'DEBUG')
        levels = [{
            'level': 'INFO',
            'debug': (0, 0),
            'info': (1, 0),
            'error': (0, 1),
        }, {
            'level': 'ERROR',
            'debug': (0, 0),
            'info': (0, 0),
            'error': (0, 1),
        }, {
            'level': 'CRITICAL',
            'debug': (0, 0),
            'info': (0, 0),
            'error': (0, 0),
        }, {
            'level': 'DEBUG',
            'debug': (1, 0),
            'info': (1, 0),
            'error': (0, 1),
        }]
        for levelTest in levels:
            resp = self.request(
                method='PUT', path='/system/log/level', user=self.users[0],
                params={'level': levelTest['level']})
            self.assertStatusOk(resp)
            self.assertEqual(resp.json, levelTest['level'])
            resp = self.request(path='/system/log/level', user=self.users[0])
            self.assertStatusOk(resp)
            self.assertEqual(resp.json, levelTest['level'])
            for level in ('debug', 'info', 'error'):
                infoCount, errorCount = infoEmit.call_count, errorEmit.call_count
                getattr(logger, level)('log entry %s %s' % (
                    levelTest['level'], level))
                self.assertEqual(infoEmit.call_count, infoCount + levelTest[level][0])
                self.assertEqual(errorEmit.call_count, errorCount + levelTest[level][1])
        # Try to set a bad log level
        resp = self.request(
            method='PUT', path='/system/log/level', user=self.users[0],
            params={'level': 'NOSUCHLEVEL'})
        self.assertStatus(resp, 400)
        self.assertIn('Invalid value for level', resp.json['message'])

    def testAccessFlags(self):
        resp = self.request('/system/access_flag')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {})

        registerAccessFlag('my_key', name='hello', description='a custom flag')

        resp = self.request('/system/access_flag')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            'my_key': {
                'name': 'hello',
                'description': 'a custom flag',
                'admin': False
            }
        })

        self.users[1] = User().load(self.users[1]['_id'], force=True)
        user = self.users[1]

        # Manage custom access flags on an access controlled resource
        self.assertFalse(User().hasAccessFlags(user, user, flags=['my_key']))

        # Admin should always have permission
        self.assertTrue(User().hasAccessFlags(user, self.users[0], flags=['my_key']))

        # Test the requireAccessFlags method
        with self.assertRaises(AccessException):
            User().requireAccessFlags(user, user=user, flags='my_key')

        User().requireAccessFlags(user, user=self.users[0], flags='my_key')

        acl = User().getFullAccessList(user)
        self.assertEqual(acl['users'][0]['flags'], [])

        # Test loadmodel requiredFlags argument via REST endpoint
        resp = self.request(
            '/test_endpoints/loadmodel_with_flags/%s' % user['_id'], user=self.users[1])
        self.assertStatus(resp, 403)

        user = User().setAccessList(self.users[0], access={
            'users': [{
                'id': self.users[1]['_id'],
                'level': AccessType.ADMIN,
                'flags': ['my_key', 'not a registered flag']
            }],
            'groups': [{
                'id': self.group['_id'],
                'level': AccessType.ADMIN,
                'flags': ['my_key']
            }]
        }, save=True)

        resp = self.request(
            '/test_endpoints/loadmodel_with_flags/%s' % user['_id'], user=self.users[1])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 'success')

        # Only registered flags should be stored
        acl = User().getFullAccessList(user)
        self.assertEqual(acl['users'][0]['flags'], ['my_key'])
        self.assertTrue(User().hasAccessFlags(user, user, flags=['my_key']))

        # Create an admin-only access flag
        registerAccessFlag('admin_flag', name='admin flag', admin=True)

        # Non-admin shouldn't be able to set it
        user = User().setAccessList(self.users[0], access={
            'users': [{
                'id': self.users[1]['_id'],
                'level': AccessType.ADMIN,
                'flags': ['admin_flag']
            }],
            'groups': []
        }, save=True, user=self.users[1])

        acl = User().getFullAccessList(user)
        self.assertEqual(acl['users'][0]['flags'], [])

        # Admin user should be able to set it
        user = User().setAccessList(self.users[1], access={
            'users': [{
                'id': self.users[1]['_id'],
                'level': AccessType.ADMIN,
                'flags': ['admin_flag']
            }],
            'groups': [{
                'id': self.group['_id'],
                'level': AccessType.ADMIN,
                'flags': ['admin_flag']
            }]
        }, save=True, user=self.users[0])

        acl = User().getFullAccessList(user)
        self.assertEqual(acl['users'][0]['flags'], ['admin_flag'])

        # An already-enabled admin-only flag should stay enabled for non-admin user
        user = User().setAccessList(self.users[1], access={
            'users': [{
                'id': self.users[1]['_id'],
                'level': AccessType.ADMIN,
                'flags': ['my_key', 'admin_flag']
            }],
            'groups': [{
                'id': self.group['_id'],
                'level': AccessType.ADMIN,
                'flags': ['admin_flag']
            }]
        }, save=True, user=self.users[1])

        acl = User().getFullAccessList(user)
        self.assertEqual(set(acl['users'][0]['flags']), {'my_key', 'admin_flag'})
        self.assertEqual(acl['groups'][0]['flags'], ['admin_flag'])

        # Test setting public flags on a collection and folder
        collectionModel = Collection()
        folderModel = Folder()
        itemModel = Item()
        collection = collectionModel.createCollection('coll', creator=self.users[0], public=True)
        folder = folderModel.createFolder(
            collection, 'folder', parentType='collection', creator=self.users[0])

        # Add an item to the folder so we can test AclMixin flag behavior
        item = itemModel.createItem(folder=folder, name='test', creator=self.users[0])

        folder = folderModel.setUserAccess(
            folder, self.users[1], level=AccessType.ADMIN, save=True, currentUser=self.users[0])

        with self.assertRaises(AccessException):
            collectionModel.requireAccessFlags(collection, user=None, flags='my_key')

        # Test AclMixin flag behavior
        with self.assertRaises(AccessException):
            itemModel.requireAccessFlags(item, user=None, flags='my_key')

        self.assertFalse(itemModel.hasAccessFlags(item, user=None, flags='my_key'))

        collection = collectionModel.setAccessList(
            collection, access=collection['access'], save=True, recurse=True, user=self.users[0],
            publicFlags=['my_key'])
        collectionModel.requireAccessFlags(collection, user=None, flags='my_key')

        # Make sure recursive setting of public flags worked
        folder = folderModel.load(folder['_id'], force=True)
        self.assertEqual(folder['publicFlags'], ['my_key'])

        itemModel.requireAccessFlags(item, user=None, flags='my_key')

        # Non-admin shouldn't be able to set admin-only public flags
        folder = folderModel.setPublicFlags(
            folder, flags=['admin_flag'], user=self.users[1], save=True)
        self.assertEqual(folder['publicFlags'], [])

        # Admin users should be able to set admin-only public flags
        folder = folderModel.setPublicFlags(
            folder, flags=['admin_flag'], user=self.users[0], save=True, append=True)
        self.assertEqual(folder['publicFlags'], ['admin_flag'])

        # Non-admin users can set admin-only public flags if they are already enabled
        folder = folderModel.setPublicFlags(
            folder, flags=['admin_flag', 'my_key'], user=self.users[1], save=True)
        self.assertEqual(set(folder['publicFlags']), {'admin_flag', 'my_key'})

        # Test "force" options
        folder = folderModel.setPublicFlags(folder, flags='admin_flag', force=True, save=True)
        self.assertEqual(folder['publicFlags'], ['admin_flag'])

        folder = folderModel.setAccessList(folder, access={
            'users': [{
                'id': self.users[1]['_id'],
                'level': AccessType.ADMIN,
                'flags': ['my_key', 'admin_flag']
            }],
            'groups': []
        }, save=True, force=True)
        folderModel.requireAccessFlags(folder, user=self.users[1], flags='my_key')

        folder = folderModel.setUserAccess(
            folder, self.users[1], level=AccessType.READ, save=True, force=True, flags=[])
        self.assertFalse(folderModel.hasAccessFlags(folder, self.users[1], flags='my_key'))

        folder = folderModel.setGroupAccess(
            folder, self.group, level=AccessType.READ, save=True, force=True, flags='my_key')
        folderModel.requireAccessFlags(folder, user=self.users[1], flags='my_key')

        # Testing with flags=None should give sensible behavior
        folderModel.requireAccessFlags(folder, user=None, flags=None)

        # Test filtering results by access flags (both ACModel and AclMixin)
        for model, doc in ((folderModel, folder), (itemModel, item)):
            cursor = model.find({})
            self.assertGreater(len(list(cursor)), 0)

            cursor = model.find({})
            filtered = list(model.filterResultsByPermission(
                cursor, user=None, level=AccessType.READ, flags='my_key'))
            self.assertEqual(len(filtered), 0)

            cursor = model.find({})
            filtered = list(model.filterResultsByPermission(
                cursor, user=self.users[1], level=AccessType.READ, flags=('my_key', 'admin_flag')))
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]['_id'], doc['_id'])

    def testServerRootSetting(self):
        settingModel = Setting()
        with self.assertRaises(ValidationException):
            settingModel.set(SettingKey.SERVER_ROOT, 'bad_value')

        settingModel.set(SettingKey.SERVER_ROOT, 'https://somedomain.org/foo')
        self.assertEqual(getApiUrl(), 'https://somedomain.org/foo/api/v1')

    def testCollectionCreationPolicySettingAndItsAccessAPI(self):
        resp = self.request(path='/system/setting', method='PUT', params={
            'list': json.dumps([
                {'key': SettingKey.COLLECTION_CREATE_POLICY, 'value': json.dumps({
                    'open': True,
                    'users': [str(self.users[1]['_id'])],
                    'groups': [str(self.group['_id'])]
                })}
            ])
        }, user=self.users[0])
        self.assertStatusOk(resp)

        resp = self.request(path='/system/setting/collection_creation_policy/access',
                            method='GET', user=self.users[0])
        self.assertEqual(resp.json['users'][0]['id'], str(self.users[1]['_id']))
        self.assertEqual(resp.json['users'][0]['login'], str(self.users[1]['login']))
        self.assertEqual(resp.json['groups'][0]['id'], str(self.group['_id']))

        # Delete underlying users and groups, should be OK
        Group().remove(self.group)
        User().remove(self.users[1])
        resp = self.request(
            path='/system/setting/collection_creation_policy/access', method='GET',
            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['users'], [])
        self.assertEqual(resp.json['groups'], [])
