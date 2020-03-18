# -*- coding: utf-8 -*-
import datetime
import json
import os

from tests import base
from girder.constants import AssetstoreType
from girder.exceptions import ValidationException
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey
from girder.utility.system import formatSize

from girder_user_quota.settings import PluginSettings


def setUpModule():
    base.enabledPlugins.append('user_quota')
    base.startServer()


def tearDownModule():
    base.stopServer()
    base.dropAllTestDatabases()


class QuotaTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'admin@girder.test',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = User().createUser(**admin)
        user = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = User().createUser(**user)
        coll = {
            'name': 'Test Collection',
            'description': 'The description',
            'public': True,
            'creator': self.admin
        }
        self.collection = Collection().createCollection(**coll)
        Folder().createFolder(
            parent=self.collection, parentType='collection', name='Public',
            public=True, creator=self.admin)

    def _uploadFile(self, name, parent, parentType='folder', size=1024,
                    error=None, partial=False, validationError=None):
        """
        Upload a random file to an item.

        :param name: name of the file.
        :param parent: parent document to upload the file to.
        :param parentType: type of parent to upload to.
        :param size: size of the file to upload
        :param error: if set, expect this error.
        :param partial: if set, return before uploading the data.  This returns
                        a kwargs for self.request so that the caller can
                        finish the upload later.
        :returns: file: the created file object
        """
        if parentType != 'file':
            resp = self.request(
                path='/file', method='POST', user=self.admin, params={
                    'parentType': parentType,
                    'parentId': parent['_id'],
                    'name': name,
                    'size': size,
                    'mimeType': 'application/octet-stream'
                }, exception=error is not None)
        else:
            resp = self.request(
                path='/file/%s/contents' % str(parent['_id']), method='PUT',
                user=self.admin, params={
                    'size': size,
                }, exception=error is not None)
        if error:
            self.assertStatus(resp, 500)
            self.assertEqual(resp.json['type'], 'girder')
            self.assertEqual(resp.json['message'][:len(error)], error)
            return None
        elif validationError:
            self.assertStatus(resp, 400)
            self.assertEqual(resp.json['type'], 'validation')
            self.assertEqual(resp.json['message'][:len(validationError)], validationError)
            return None
        # We don't create the contents until after we check for the first
        # error.  This means that we can try to upload huge files without
        # allocating the space for them
        contents = os.urandom(size)
        self.assertStatusOk(resp)
        upload = resp.json
        if partial:
            body = contents[:-1]
        else:
            body = contents

        resp = self.request(path='/file/chunk', method='POST', user=self.admin, body=body, params={
            'uploadId': upload['_id']
        }, type='application/octet-stream')
        self.assertStatusOk(resp)
        if partial:
            return {
                'path': '/file/chunk',
                'method': 'POST',
                'user': self.admin,
                'body': contents[-1:],
                'type': 'application/octet-stream',
                'params': {
                    'offset': len(contents) - 1,
                    'uploadId': upload['_id']
                }
            }
        return resp.json

    def _setPolicy(self, policy, model, resource, user, error=None, results=None):
        """
        Set the quota or assetstore policy and check that it was set.

        :param policy: dictionary of values to set.
        :param model: either 'user' or 'collection'.
        :param resource: the document for the resource to test.
        :param user: user to use for authorization.
        :param error: if set, this is a substring expected in an error message.
        :param results: if not specified, we expect policy to match the set
                        results.  Otherwise, these are the expected results.
        """
        if isinstance(policy, dict):
            policyJSON = json.dumps(policy)
        else:
            policyJSON = policy
        path = '/%s/%s/quota' % (model, resource['_id'])
        resp = self.request(path=path, method='PUT', user=user,
                            params={'policy': policyJSON})
        if error:
            self.assertStatus(resp, 400)
            self.assertIn(error, resp.json['message'])
            return
        self.assertStatusOk(resp)
        resp = self.request(path=path, method='GET', user=user)
        self.assertStatusOk(resp)
        currentPolicy = resp.json['quota']
        if not results:
            results = policy
        for key in results:
            if results[key] or results[key] == 0 or results[key] is False:
                self.assertEqual(currentPolicy[key], results[key])
            else:
                self.assertEqual(currentPolicy[key], None)

    def _setQuotaDefault(self, model, value, testVal='__NOCHECK__',
                         error=None):
        """
        Set the default quota for a particular model.

        :param model: either 'user' or 'collection'.
        :param value: the value to set.  Either None or a positive integer.
        :param testVal: if not __NOCHECK__, test the current value to see if it
                        matches this.
        :param error: if set, this is a substring expected in an error message.
        """
        if model == 'user':
            key = PluginSettings.DEFAULT_USER_QUOTA
        elif model == 'collection':
            key = PluginSettings.DEFAULT_COLLECTION_QUOTA
        try:
            Setting().set(key, value)
        except ValidationException as err:
            if not error:
                raise
            if error not in err.args[0]:
                raise
            return
        if testVal != '__NOCHECK__':
            newVal = Setting().get(key)
            self.assertEqual(newVal, testVal)

    def _testAssetstores(self, model, resource, user):
        """
        Test assetstore policies for a specified resource.

        :param model: either 'user' or 'collection'.
        :param resource: the document for the resource to test.
        :param user: user to use for authorization.
        """
        resp = self.request(path='/folder', method='GET', user=user,
                            params={'parentType': model,
                                    'parentId': resource['_id']})
        self.assertStatusOk(resp)
        self.assertGreaterEqual(len(resp.json), 1)
        folder = resp.json[0]
        curAssetstoreId = str(self.currentAssetstore['_id'])
        altAssetstoreId = str(self.alternateAssetstore['_id'])
        badAssetstoreId = str(self.brokenAssetstore['_id'])
        invalidAssetstoreId = str(folder['_id'])
        file = self._uploadFile('Upload to Current', folder)
        self.assertEqual(file['assetstoreId'], curAssetstoreId)
        # A simple preferredASsetstore policy should work
        self._setPolicy({'preferredAssetstore': altAssetstoreId},
                        model, resource, user)
        file = self._uploadFile('Upload to Alt', folder)
        self.assertEqual(file['assetstoreId'], altAssetstoreId)
        # Uploading to an invalid preferredAssetstore policy should send the
        # data to the current asssetstore
        self._setPolicy({'preferredAssetstore': invalidAssetstoreId},
                        model, resource, user)
        file = self._uploadFile('Upload to Invalid', folder)
        self.assertEqual(file['assetstoreId'], curAssetstoreId)
        # Uploading to an unreachable preferredAssetstore policy should send
        # the data to the current asssetstore
        self._setPolicy({'preferredAssetstore': badAssetstoreId},
                        model, resource, user)
        file = self._uploadFile('Upload to Bad', folder)
        self.assertEqual(file['assetstoreId'], curAssetstoreId)
        # We can specify a fallback
        self._setPolicy({'fallbackAssetstore': altAssetstoreId},
                        model, resource, user)
        file = self._uploadFile('Upload to Bad with fallback', folder)
        self.assertEqual(file['assetstoreId'], altAssetstoreId)
        # Or say there shouldn't be a fallback
        self._setPolicy({'fallbackAssetstore': 'none'},
                        model, resource, user)
        self._uploadFile('Upload to Bad with no fallback', folder,
                         error='Required assetstore is unavailable')
        # if we clear the preferred policy, the fallback shouldn't matter.
        self._setPolicy({'preferredAssetstore': ''},
                        model, resource, user)
        file = self._uploadFile('Upload with not preferred', folder)
        self.assertEqual(file['assetstoreId'], curAssetstoreId)

    def _testQuota(self, model, resource, user):
        """
        Test quota policies for a specified resource.

        :param model: either 'user' or 'collection'.
        :param resource: the document for the resource to test.
        :param user: user to use for authorization.
        """
        Setting().set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 0)
        resp = self.request(path='/folder', method='GET', user=user,
                            params={'parentType': model,
                                    'parentId': resource['_id']})
        self.assertStatusOk(resp)
        self.assertGreaterEqual(len(resp.json), 1)
        folder = resp.json[0]
        # Set 0 b quota so nothing can be uploaded
        self._setQuotaDefault(model, 0)
        # Upload one file, it should fail
        self._uploadFile(
            'File too large',
            folder,
            size=1024,
            validationError='Upload would exceed file storage quota',
        )
        # Upload a tiny file, it should also fail
        self._uploadFile(
            'File too large',
            folder,
            size=1,
            validationError='Upload would exceed file storage quota',
        )
        # Set quota to None so anything can be uploaded
        self._setQuotaDefault(model, None)
        # Set a 0 b policy so nothing can be uploaded
        self._setPolicy({'fileSizeQuota': 0, 'useQuotaDefault': False},
                        model, resource, user)
        # Upload one file, it should fail
        self._uploadFile(
            'File too large',
            folder,
            size=1024,
            validationError='Upload would exceed file storage quota',
        )
        # Upload a tiny file, it should also fail
        self._uploadFile(
            'File too large',
            folder,
            size=1,
            validationError='Upload would exceed file storage quota',
        )
        # Reset the policy to use the default so anything can be uploaded
        self._setPolicy({'useQuotaDefault': True}, model, resource, user)
        # Upload one file so that there is some use
        self._uploadFile('First upload', folder, size=1024)
        # Set a policy limiting things to 4 kb, then a 4 kb file should fail
        self._setPolicy({'fileSizeQuota': 4096, 'useQuotaDefault': False},
                        model, resource, user)
        self._uploadFile('File too large', folder, size=4096,
                         validationError='Upload would exceed file storage quota')
        # But a 2 kb file will succeed
        file = self._uploadFile('Second upload', folder, size=2048)
        # And a second 2 kb file will fail
        self._uploadFile('File too large', folder, size=2048,
                         validationError='Upload would exceed file storage quota')
        # If we start uploading two files, only one should complete
        file1kwargs = self._uploadFile('First partial', folder, size=768,
                                       partial=True)
        file2kwargs = self._uploadFile('Second partial', folder, size=768,
                                       partial=True)
        resp = self.request(**file1kwargs)
        self.assertStatusOk(resp)
        try:
            resp = self.request(**file2kwargs)
            self.assertStatus(resp, 400)
        except AssertionError as exc:
            self.assertTrue('Upload exceeded' in exc.args[0])
        # Shrink the quota to smaller than all of our files.  Replacing an
        # existing file should still work, though
        self._setPolicy({'fileSizeQuota': 2048}, model, resource, user)
        self._uploadFile('Second upload', file, 'file', size=1536)
        # Now test again using default quotas.  We have 1024+1536+768 = 3328
        # bytes currently uploaded
        self._setPolicy({'useQuotaDefault': True}, model, resource, user)
        # Upload should now be unlimited, so anything will work
        self._uploadFile('Fourth upload', folder, size=1792)
        # Set a policy limiting things to 8 kb, then an additional 4 kb file
        # should fail
        self._setQuotaDefault(model, 8192)
        self._uploadFile('File too large', folder, size=4096,
                         validationError='Upload would exceed file storage quota')
        # But a 2 kb file will succeed
        file = self._uploadFile('Fifth upload', folder, size=2048)
        # And a second 2 kb file will fail
        self._uploadFile('File too large', folder, size=2048,
                         validationError='Upload would exceed file storage quota')
        # Set a policy with a large quota to test using NumberLong in the
        # mongo settings.
        self._setQuotaDefault(model, 5 * 1024**3)
        # A small file should now upload
        file = self._uploadFile('Six upload', folder, size=2048)
        # But a huge one will fail
        self._uploadFile('File too large', folder, size=6 * 1024**3,
                         validationError='Upload would exceed file storage quota')

    def testAssetstorePolicy(self):
        """
        Test assetstore policies for a user and a collection.
        """
        # We want three assetstores for testing, one of which is unreachable.
        # We already have one, which is the current assetstore.
        base.dropGridFSDatabase('girder_test_user_quota_assetstore')
        params = {
            'name': 'Non-current Store',
            'type': AssetstoreType.GRIDFS,
            'db': 'girder_test_user_quota_assetstore'
        }
        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertStatusOk(resp)

        # Create a broken assetstore. (Must bypass validation since it should
        # not let us create an assetstore in a broken state).
        Assetstore().save({
            'name': 'Broken Store',
            'type': AssetstoreType.FILESYSTEM,
            'root': '/dev/null',
            'created': datetime.datetime.utcnow()
        }, validate=False)

        # Now get the assetstores and save their ids for later
        resp = self.request(path='/assetstore', method='GET', user=self.admin,
                            params={'sort': 'created'})
        self.assertStatusOk(resp)
        assetstores = resp.json
        self.assertEqual(len(assetstores), 3)
        self.currentAssetstore = assetstores[0]
        self.alternateAssetstore = assetstores[1]
        self.brokenAssetstore = assetstores[2]
        self._testAssetstores('user', self.user, self.admin)
        self._testAssetstores('collection', self.collection, self.admin)

    def testQuotaPolicy(self):
        """
        Test quota policies for a user and a collection.
        """
        self._testQuota('user', self.user, self.admin)
        self._testQuota('collection', self.collection, self.admin)

    def testPolicySettings(self):
        """
        Test validation of policy settings.
        """
        # We have to send a json dictionary
        # We can only set certain keys
        self._setPolicy('this is not json',
                        'user', self.user, self.admin,
                        error='Parameter policy must be valid JSON.')
        self._setPolicy(json.dumps(['this is not a dictionary']),
                        'user', self.user, self.admin,
                        error='Parameter policy must be a JSON object.')
        # We can only set certain keys
        self._setPolicy({'notAKey': 'notAValue'},
                        'user', self.user, self.admin,
                        error='not a valid quota policy key')
        # We need to pass None, current, or an ObjectId to preferredAssetstore
        self._setPolicy({'preferredAssetstore': 'current'},
                        'user', self.user, self.admin,
                        results={'preferredAssetstore': None})
        self._setPolicy({'preferredAssetstore': 'not an id'},
                        'user', self.user, self.admin,
                        error='Invalid preferredAssetstore')
        self._setPolicy({'preferredAssetstore': None},
                        'user', self.user, self.admin)
        # fallbackAssetstore can also take 'none'
        self._setPolicy({'fallbackAssetstore': 'current'},
                        'user', self.user, self.admin,
                        results={'fallbackAssetstore': None})
        self._setPolicy({'fallbackAssetstore': 'none'},
                        'user', self.user, self.admin)
        self._setPolicy({'fallbackAssetstore': 'not an id'},
                        'user', self.user, self.admin,
                        error='Invalid fallbackAssetstore')
        self._setPolicy({'fallbackAssetstore': None},
                        'user', self.user, self.admin)
        # fileSizeQuota can be None, blank, 0, or a positive integer
        self._setPolicy({'fileSizeQuota': 0},
                        'user', self.user, self.admin,
                        results={'fileSizeQuota': 0})
        self._setPolicy({'fileSizeQuota': '00'},
                        'user', self.user, self.admin,
                        results={'fileSizeQuota': 0})
        self._setPolicy({'fileSizeQuota': ''},
                        'user', self.user, self.admin,
                        results={'fileSizeQuota': None})
        self._setPolicy({'fileSizeQuota': 'not an integer'},
                        'user', self.user, self.admin,
                        error='Invalid quota')
        self._setPolicy({'fileSizeQuota': -1},
                        'user', self.user, self.admin,
                        error='Invalid quota')
        self._setPolicy({'fileSizeQuota': None},
                        'user', self.user, self.admin)
        # useDefaultQuota can be True, False, None, yes, no, 0, 1.
        valdict = {None: True, True: True, 'true': True, 1: True, 'True': True,
                   False: False, 'false': False, 0: False, 'False': False}
        for val in valdict:
            self._setPolicy({'useQuotaDefault': val},
                            'user', self.user, self.admin,
                            results={'useQuotaDefault': valdict[val]})
        self._setPolicy({'useQuotaDefault': 'not_a_boolean'}, 'user',
                        self.user, self.admin, error='Invalid useQuotaDefault')
        # the resource default values behave like fileSizeQuota
        self._setQuotaDefault('user', 0, 0)
        self._setQuotaDefault('user', '00', 0)
        self._setQuotaDefault('user', '', None)
        self._setQuotaDefault('user', 'not an integer', error='Invalid quota')
        self._setQuotaDefault('user', -1, error='Invalid quota')
        self._setQuotaDefault('user', None)

    def testFormatSize(self):
        """
        Test the formatSize function
        """
        testList = [
            (0, '0 B'),
            (1000, '1000 B'),
            (10000, '10000 B'),
            (20000, '19.53 kB'),
            (200000, '195.3 kB'),
            (2000000, '1.907 MB'),
            ]
        for testItem in testList:
            self.assertEqual(testItem[1], formatSize(testItem[0]))
