import datetime
import io
import os
import shutil
import time
import unittest.mock

import boto3
import botocore.exceptions
from girder_local_checkout import tasks, utils
from girder_local_checkout.models import Checkout, CheckoutFile, CheckoutStatus
from girder_local_checkout.settings import PluginSettings
from tests import base

from girder.constants import AccessType, ROOT_DIR
from girder.exceptions import ValidationException
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from girder.utility import assetstore_utilities

BUCKET = 'bucketname'


def setUpModule():
    base.enabledPlugins.append('local_checkout')
    base.startServer(mockS3=True)


def tearDownModule():
    base.stopServer()


class LocalCheckoutTestCase(base.TestCase):
    def setUp(self):
        super().setUp()
        # Run jobs in the calling thread, so that a checkout is complete when
        # its request returns
        self._threadPatch = unittest.mock.patch.object(
            tasks, '_runInThread', lambda target, name: target())
        self._threadPatch.start()

        self.fsAssetstore = self.assetstore
        self.s3Assetstore = Assetstore().createS3Assetstore(
            name='s3', bucket=BUCKET, accessKeyId='abc', secret='123',
            service=base.mockS3Server.service, prefix='test')
        self.s3Client = boto3.client('s3', **base.mockS3Server.botoConnect)

        self.admin = User().createUser(
            email='admin@girder.test', login='admin', firstName='Admin', lastName='Admin',
            password='password', admin=True)
        self.user = User().createUser(
            email='user@girder.test', login='user', firstName='user', lastName='user',
            password='password', admin=False)
        self.folder = Folder().findOne(
            {'parentId': self.admin['_id'], 'parentCollection': 'user', 'name': 'Private'})
        self.otherRoots = []

    def tearDown(self):
        self._threadPatch.stop()
        for root in self.otherRoots:
            shutil.rmtree(root, ignore_errors=True)
        super().tearDown()

    def uploadToS3(self, folder, name, data):
        return Upload().uploadFromFile(
            io.BytesIO(data), len(data), name, parentType='folder', parent=folder,
            user=self.admin, assetstore=self.s3Assetstore)

    def download(self, file):
        """Read a file's data as the server would stream it (e.g. in a zip)."""
        file = File().load(file['_id'], force=True)
        return b''.join(File().download(file, headers=False)())

    def s3KeyExists(self, key):
        try:
            self.s3Client.head_object(Bucket=BUCKET, Key=key)
            return True
        except botocore.exceptions.ClientError:
            return False

    def localPath(self, assetstore, file):
        return os.path.join(assetstore['root'], file['path'])

    def createOtherAssetstore(self, name):
        root = os.path.join(ROOT_DIR, 'tests', 'assetstore', '%s_%s' % (
            os.environ.get('GIRDER_TEST_ASSETSTORE', 'test'), name))
        shutil.rmtree(root, ignore_errors=True)
        self.otherRoots.append(root)
        return Assetstore().createFilesystemAssetstore(name=name, root=root)

    def testCheckoutAndRelease(self):
        folder = self.folder
        sub = Folder().createFolder(folder, 'sub', creator=self.admin)
        data1 = b'hello world' * 1000
        data2 = os.urandom(1024 * 1024 + 123)
        file1 = self.uploadToS3(folder, 'one.txt', data1)
        file2 = self.uploadToS3(sub, 'two.bin', data2)
        # An empty file and a file already on the filesystem are counted but not copied
        self.uploadToS3(folder, 'empty.txt', b'')
        fsFile = Upload().uploadFromFile(
            io.BytesIO(b'local'), 5, 'local.txt', parentType='folder', parent=folder,
            user=self.admin, assetstore=self.fsAssetstore)
        s3Key1 = file1['s3Key']

        resp = self.request(path='/folder/%s/local_checkout' % folder['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertIsNone(resp.json['checkout'])
        self.assertTrue(resp.json['enabled'])
        self.assertEqual(resp.json['assetstoreName'], self.fsAssetstore['name'])
        self.assertEqual(resp.json['fileCount'], 3)
        self.assertEqual(resp.json['localCount'], 0)
        self.assertEqual(resp.json['bytes'], len(data1) + len(data2))

        resp = self.request(
            path='/folder/%s/local_checkout' % folder['_id'], method='PUT', user=self.admin,
            params={'days': 5})
        self.assertStatusOk(resp)
        checkout = Checkout().load(resp.json['_id'])
        self.assertEqual(checkout['status'], CheckoutStatus.COMPLETE)
        self.assertEqual(checkout['fileCount'], 3)
        self.assertEqual(checkout['localCount'], 3)
        self.assertEqual(checkout['bytes'], len(data1) + len(data2))
        self.assertEqual(checkout['days'], 5)

        for file, data in ((file1, data1), (file2, data2)):
            file = File().load(file['_id'], force=True)
            self.assertEqual(file['assetstoreId'], self.fsAssetstore['_id'])
            self.assertNotIn('s3Key', file)
            self.assertNotIn('relpath', file)
            self.assertEqual(os.path.getsize(self.localPath(self.fsAssetstore, file)), len(data))
            self.assertEqual(self.download(file), data)
            record = CheckoutFile().findByFile(file)
            self.assertTrue(record['original']['s3Key'])
            self.assertEqual(record['expires'], checkout['expires'])
        self.assertEqual(File().load(fsFile['_id'], force=True)['path'], fsFile['path'])
        # The original S3 data is retained
        self.assertTrue(self.s3KeyExists(s3Key1))

        resp = self.request(path='/folder/%s/local_checkout' % folder['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['checkout']['status'], CheckoutStatus.COMPLETE)
        self.assertEqual(resp.json['localCount'], 3)
        self.assertEqual(resp.json['localBytes'], len(data1) + len(data2))

        resp = self.request(path='/local_checkout', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['checkouts']), 1)
        self.assertEqual(resp.json['checkouts'][0]['folderPath'], '/user/admin/Private')
        self.assertEqual(resp.json['checkouts'][0]['userLogin'], 'admin')
        self.assertEqual(resp.json['localFileCount'], 3)
        self.assertEqual(resp.json['localBytes'], len(data1) + len(data2))
        self.assertEqual(len(resp.json['assetstores']), 1)
        self.assertEqual(resp.json['assetstores'][0]['name'], self.fsAssetstore['name'])
        self.assertEqual(resp.json['assetstores'][0]['localFileCount'], 3)
        self.assertEqual(resp.json['checkouts'][0]['assetstoreName'], self.fsAssetstore['name'])

        # The copy ran as a job owned by the user
        resp = self.request(path='/job', user=self.admin, params={'userId': self.admin['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['type'], 'local_checkout.checkout')
        self.assertEqual(resp.json[0]['status'], 3)  # JobStatus.SUCCESS

        # Release
        localFile1 = File().load(file1['_id'], force=True)
        resp = self.request(
            path='/folder/%s/local_checkout' % folder['_id'], method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertTrue(resp.json['released'])
        self.assertIsNone(Checkout().findByFolder(folder))
        self.assertEqual(CheckoutFile().find().count(), 0)
        self.assertFalse(os.path.exists(self.localPath(self.fsAssetstore, localFile1)))
        file1 = File().load(file1['_id'], force=True)
        self.assertEqual(file1['assetstoreId'], self.s3Assetstore['_id'])
        self.assertEqual(file1['s3Key'], s3Key1)
        self.assertNotIn('path', file1)
        self.assertEqual(self.download(file1), data1)

        resp = self.request(
            path='/folder/%s/local_checkout' % folder['_id'], method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertFalse(resp.json['released'])

    def testDurationChangesAndExpiry(self):
        folder = self.folder
        file = self.uploadToS3(folder, 'one.txt', b'data')
        sub = Folder().createFolder(folder, 'sub', creator=self.admin)
        subFile = self.uploadToS3(sub, 'two.txt', b'more data')

        def put(fold, days):
            resp = self.request(
                path='/folder/%s/local_checkout' % fold['_id'], method='PUT', user=self.admin,
                params={'days': days})
            self.assertStatusOk(resp)
            return resp.json

        # The subfolder is checked out longer than its parent
        put(sub, 10)
        put(folder, 3)
        subCheckout = Checkout().findByFolder(sub)
        folderCheckout = Checkout().findByFolder(folder)
        fileRecord = CheckoutFile().findByFile(file)
        subRecord = CheckoutFile().findByFile(subFile)
        self.assertEqual(fileRecord['expires'], folderCheckout['expires'])
        self.assertEqual(subRecord['expires'], subCheckout['expires'])
        self.assertEqual(set(subRecord['checkoutIds']),
                         {subCheckout['_id'], folderCheckout['_id']})

        # Extending the parent beyond the subfolder extends the subfolder's file
        put(folder, 20)
        folderCheckout = Checkout().findByFolder(folder)
        self.assertEqual(CheckoutFile().findByFile(subFile)['expires'],
                         folderCheckout['expires'])
        # Shortening it again falls back to the subfolder's checkout
        put(folder, 1)
        self.assertEqual(CheckoutFile().findByFile(subFile)['expires'], subCheckout['expires'])

        # Releasing the parent keeps the subfolder's file local
        put(folder, 0)
        self.assertIsNone(Checkout().findByFolder(folder))
        self.assertIsNone(CheckoutFile().findByFile(file))
        self.assertEqual(File().load(file['_id'], force=True)['assetstoreId'],
                         self.s3Assetstore['_id'])
        self.assertEqual(CheckoutFile().findByFile(subFile)['checkoutIds'],
                         [subCheckout['_id']])
        self.assertEqual(File().load(subFile['_id'], force=True)['assetstoreId'],
                         self.fsAssetstore['_id'])

        # Cleanup does nothing until the checkout expires
        resp = self.request(path='/local_checkout/cleanup', method='POST', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['released'], 0)
        past = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        Checkout().update({'_id': subCheckout['_id']}, {'$set': {'expires': past}})
        CheckoutFile().update({'_id': subRecord['_id']}, {'$set': {'expires': past}})
        resp = self.request(path='/local_checkout/cleanup', method='POST', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['released'], 1)
        self.assertIsNone(Checkout().findByFolder(sub))
        self.assertIsNone(CheckoutFile().findByFile(subFile))
        self.assertEqual(File().load(subFile['_id'], force=True)['assetstoreId'],
                         self.s3Assetstore['_id'])
        self.assertEqual(self.download(subFile), b'more data')

    def testFileDeletionAndReplacement(self):
        folder = self.folder
        file1 = self.uploadToS3(folder, 'one.txt', b'data one')
        file2 = self.uploadToS3(folder, 'two.txt', b'data two')
        resp = self.request(
            path='/folder/%s/local_checkout' % folder['_id'], method='PUT', user=self.admin,
            params={'days': 5})
        self.assertStatusOk(resp)
        localFile1 = File().load(file1['_id'], force=True)

        # The S3 assetstore cannot be deleted while it holds a checked-out file's original data
        with self.assertRaisesRegex(ValidationException, 'original data'):
            Assetstore().remove(self.s3Assetstore)
        resp = self.request(path='/assetstore/%s' % self.s3Assetstore['_id'], method='DELETE',
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIsNotNone(Assetstore().load(self.s3Assetstore['_id']))

        # Deleting a checked-out file removes the local copy and the S3 original
        resp = self.request(path='/file/%s' % file1['_id'], method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertIsNone(CheckoutFile().findByFile(file1))
        self.assertFalse(os.path.exists(self.localPath(self.fsAssetstore, localFile1)))
        self.assertFalse(self.s3KeyExists(file1['s3Key']))

        # Replacing the contents of a checked-out file likewise drops the original
        upload = Upload().createUploadToFile(
            File().load(file2['_id'], force=True), self.admin, 12, assetstore=self.fsAssetstore)
        Upload().handleChunk(upload, io.BytesIO(b'new contents'))
        self.assertIsNone(CheckoutFile().findByFile(file2))
        self.assertFalse(self.s3KeyExists(file2['s3Key']))
        self.assertEqual(self.download(file2), b'new contents')
        self.assertIsNotNone(Checkout().findByFolder(folder))

        # Deleting the folder removes the checkout
        resp = self.request(path='/folder/%s' % folder['_id'], method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertIsNone(Checkout().findByFolder(folder))

    def testInsufficientSpace(self):
        folder = self.folder
        folderA = Folder().createFolder(folder, 'A', creator=self.admin)
        folderB = Folder().createFolder(folder, 'B', creator=self.admin)
        fileA = self.uploadToS3(folderA, 'a.txt', b'a' * 100)
        fileB = self.uploadToS3(folderB, 'b.txt', b'b' * 100)

        # Pretend the assetstore only has room for one of the files
        def freeSpace(adapter):
            return 150 - sum(record['size'] for record in CheckoutFile().find())

        with unittest.mock.patch.object(utils, 'freeSpace', freeSpace):
            resp = self.request(
                path='/folder/%s/local_checkout' % folderA['_id'], method='PUT',
                user=self.admin, params={'days': 2})
            self.assertStatusOk(resp)
            self.assertEqual(Checkout().findByFolder(folderA)['status'], CheckoutStatus.COMPLETE)
            self.assertIsNotNone(CheckoutFile().findByFile(fileA))

            # A longer checkout evicts the shorter one when space runs out
            resp = self.request(
                path='/folder/%s/local_checkout' % folderB['_id'], method='PUT',
                user=self.admin, params={'days': 10})
            self.assertStatusOk(resp)
            self.assertEqual(Checkout().findByFolder(folderB)['status'], CheckoutStatus.COMPLETE)
            self.assertIsNotNone(CheckoutFile().findByFile(fileB))
            self.assertIsNone(CheckoutFile().findByFile(fileA))
            self.assertEqual(File().load(fileA['_id'], force=True)['assetstoreId'],
                             self.s3Assetstore['_id'])
            checkoutA = Checkout().findByFolder(folderA)
            self.assertEqual(checkoutA['status'], CheckoutStatus.PARTIAL)
            self.assertEqual(checkoutA['localCount'], 0)

            # A shorter checkout cannot evict the longer one and is left partial
            resp = self.request(
                path='/folder/%s/local_checkout' % folderA['_id'], method='PUT',
                user=self.admin, params={'days': 3})
            self.assertStatusOk(resp)
            checkoutA = Checkout().findByFolder(folderA)
            self.assertEqual(checkoutA['status'], CheckoutStatus.PARTIAL)
            self.assertIn('Insufficient space', checkoutA['message'])
            self.assertIsNone(CheckoutFile().findByFile(fileA))
            self.assertIsNotNone(CheckoutFile().findByFile(fileB))

            # An upload to the filesystem assetstore evicts checkouts of any
            # duration rather than failing
            uploaded = Upload().uploadFromFile(
                io.BytesIO(b'c' * 100), 100, 'c.txt', parentType='folder', parent=folder,
                user=self.admin, assetstore=self.fsAssetstore)
            self.assertEqual(uploaded['assetstoreId'], self.fsAssetstore['_id'])
            self.assertEqual(self.download(uploaded), b'c' * 100)
            self.assertIsNone(CheckoutFile().findByFile(fileB))
            self.assertEqual(File().load(fileB['_id'], force=True)['assetstoreId'],
                             self.s3Assetstore['_id'])
            self.assertEqual(Checkout().findByFolder(folderB)['status'], CheckoutStatus.PARTIAL)
            self.assertEqual(self.download(fileB), b'b' * 100)

    def testPermissionsAndSettings(self):
        folder = self.folder
        self.uploadToS3(folder, 'one.txt', b'data')
        Folder().setUserAccess(folder, self.user, level=AccessType.WRITE, save=True)
        path = '/folder/%s/local_checkout' % folder['_id']

        resp = self.request(path=path, method='PUT', user=self.user, params={'days': 1000})
        self.assertStatus(resp, 400)
        self.assertIn('may not exceed', resp.json['message'])

        Setting().set(PluginSettings.ADMIN_ONLY, True)
        resp = self.request(path=path, method='PUT', user=self.user, params={'days': 1})
        self.assertStatus(resp, 403)
        resp = self.request(path=path, user=self.user)
        self.assertStatusOk(resp)
        self.assertTrue(resp.json['adminOnly'])
        Setting().set(PluginSettings.ADMIN_ONLY, False)

        resp = self.request(path='/local_checkout', user=self.user)
        self.assertStatus(resp, 403)

        # The settings that decide who sees the menu item are public
        resp = self.request(path='/local_checkout/settings')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {'adminOnly': False, 'maxDays': 90})

        # Point the plugin at the S3 assetstore: not allowed
        with self.assertRaises(ValidationException):
            Setting().set(PluginSettings.ASSETSTORE_ID, str(self.s3Assetstore['_id']))
        Setting().set(PluginSettings.ASSETSTORE_ID, str(self.fsAssetstore['_id']))
        self.assertEqual(utils.getTargetAssetstore()['_id'], self.fsAssetstore['_id'])
        Setting().set(PluginSettings.ASSETSTORE_ID, '')

        # With an S3 assetstore as the default and no filesystem assetstore,
        # the feature is disabled
        Assetstore().update({'_id': self.fsAssetstore['_id']}, {'$set': {'current': False}})
        Assetstore().update({'_id': self.s3Assetstore['_id']}, {'$set': {'current': True}})
        Assetstore().update({'_id': self.fsAssetstore['_id']}, {'$set': {'type': -1}})
        resp = self.request(path=path, user=self.user)
        self.assertStatusOk(resp)
        self.assertFalse(resp.json['enabled'])
        self.assertEqual(resp.json['assetstores'], [])
        resp = self.request(path=path, method='PUT', user=self.user, params={'days': 1})
        self.assertStatus(resp, 400)
        self.assertIn('No filesystem assetstore', resp.json['message'])
        Assetstore().update({'_id': self.fsAssetstore['_id']}, {'$set': {
            'type': self.fsAssetstore['type']}})
        Assetstore().update({'_id': self.s3Assetstore['_id']}, {'$set': {'current': False}})
        Assetstore().update({'_id': self.fsAssetstore['_id']}, {'$set': {'current': True}})

        resp = self.request(path=path, method='PUT', user=self.user, params={'days': 1})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['userId'], str(self.user['_id']))
        self.assertEqual(Checkout().findByFolder(folder)['status'], CheckoutStatus.COMPLETE)

    def testChooseAssetstore(self):
        folder = self.folder
        file = self.uploadToS3(folder, 'one.txt', b'data')
        path = '/folder/%s/local_checkout' % folder['_id']
        Assetstore().update({'_id': self.fsAssetstore['_id']}, {'$set': {'current': False}})
        Assetstore().update({'_id': self.s3Assetstore['_id']}, {'$set': {'current': True}})

        # With S3 as the default and one filesystem assetstore, it is offered
        # and used without having to be named
        resp = self.request(path=path, user=self.admin)
        self.assertStatusOk(resp)
        self.assertTrue(resp.json['enabled'])
        self.assertIsNone(resp.json['assetstoreName'])
        self.assertEqual([a['_id'] for a in resp.json['assetstores']],
                         [str(self.fsAssetstore['_id'])])
        resp = self.request(path=path, method='PUT', user=self.admin, params={'days': 1})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['assetstoreId'], str(self.fsAssetstore['_id']))
        self.assertEqual(File().load(file['_id'], force=True)['assetstoreId'],
                         self.fsAssetstore['_id'])
        resp = self.request(path=path, method='DELETE', user=self.admin)
        self.assertStatusOk(resp)

        # With several, one must be chosen, and it must be a filesystem assetstore
        other = self.createOtherAssetstore('other')
        resp = self.request(path=path, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual({a['name'] for a in resp.json['assetstores']},
                         {self.fsAssetstore['name'], 'other'})
        resp = self.request(path=path, method='PUT', user=self.admin, params={'days': 1})
        self.assertStatus(resp, 400)
        self.assertIn('Choose', resp.json['message'])
        resp = self.request(path=path, method='PUT', user=self.admin, params={
            'days': 1, 'assetstoreId': str(self.s3Assetstore['_id'])})
        self.assertStatus(resp, 400)
        resp = self.request(path=path, method='PUT', user=self.admin, params={
            'days': 1, 'assetstoreId': str(other['_id'])})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['assetstoreId'], str(other['_id']))
        local = File().load(file['_id'], force=True)
        self.assertEqual(local['assetstoreId'], other['_id'])
        self.assertTrue(os.path.isfile(self.localPath(other, local)))
        self.assertEqual(CheckoutFile().findByFile(file)['localAssetstoreId'], other['_id'])

        # Changing the duration keeps the chosen assetstore
        resp = self.request(path=path, method='PUT', user=self.admin, params={'days': 3})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['assetstoreId'], str(other['_id']))

        resp = self.request(path='/local_checkout', user=self.admin)
        self.assertStatusOk(resp)
        byName = {a['name']: a for a in resp.json['assetstores']}
        self.assertEqual(byName['other']['localFileCount'], 1)
        self.assertEqual(byName[self.fsAssetstore['name']]['localFileCount'], 0)
        self.assertEqual(resp.json['checkouts'][0]['assetstoreName'], 'other')

        # Releasing restores the S3 data from the chosen assetstore
        resp = self.request(path=path, method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertFalse(os.path.exists(self.localPath(other, local)))
        self.assertEqual(File().load(file['_id'], force=True)['assetstoreId'],
                         self.s3Assetstore['_id'])
        self.assertEqual(self.download(file), b'data')

    def testConcurrentCheckouts(self):
        """
        Two checkouts that both decide to copy the same file (e.g. of a folder
        and its subfolder, run at the same time) must end up sharing one local
        copy.
        """
        folder = self.folder
        file = self.uploadToS3(folder, 'one.txt', b'shared data')
        sub = Folder().createFolder(folder, 'sub', creator=self.admin)
        checkoutA = Checkout().createCheckout(folder, self.admin, 2, self.fsAssetstore)
        checkoutB = Checkout().createCheckout(sub, self.admin, 5, self.fsAssetstore)
        adapter = assetstore_utilities.getAssetstoreAdapter(self.fsAssetstore)

        # Both tasks gathered the file before either copied it
        staleFile = dict(file)
        recordA = utils.makeLocal(file, self.fsAssetstore, adapter, checkoutA)
        recordB = utils.makeLocal(staleFile, self.fsAssetstore, adapter, checkoutB)
        self.assertEqual(recordB['_id'], recordA['_id'])
        self.assertEqual(CheckoutFile().find().count(), 1)
        record = CheckoutFile().findByFile(file)
        self.assertEqual(set(record['checkoutIds']), {checkoutA['_id'], checkoutB['_id']})
        self.assertEqual(record['expires'], Checkout().load(checkoutB['_id'])['expires'])
        local = File().load(file['_id'], force=True)
        self.assertEqual(local['assetstoreId'], self.fsAssetstore['_id'])
        self.assertTrue(os.path.isfile(self.localPath(self.fsAssetstore, local)))
        self.assertEqual(self.download(file), b'shared data')

        # Releasing one checkout keeps the copy; releasing both restores the original
        utils.removeCheckout(checkoutA)
        self.assertIsNotNone(CheckoutFile().findByFile(file))
        self.assertEqual(self.download(file), b'shared data')
        utils.removeCheckout(checkoutB)
        self.assertIsNone(CheckoutFile().findByFile(file))
        self.assertFalse(os.path.exists(self.localPath(self.fsAssetstore, local)))
        self.assertEqual(File().load(file['_id'], force=True)['assetstoreId'],
                         self.s3Assetstore['_id'])
        self.assertEqual(self.download(file), b'shared data')

    def testAsynchronousJob(self):
        """
        With a real thread, the checkout runs in the background and the
        request returns a pending checkout.
        """
        self._threadPatch.stop()
        folder = self.folder
        file = self.uploadToS3(folder, 'one.txt', b'data')
        resp = self.request(
            path='/folder/%s/local_checkout' % folder['_id'], method='PUT', user=self.admin,
            params={'days': 1})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['status'], CheckoutStatus.PENDING)
        for _ in range(600):
            checkout = Checkout().findByFolder(folder)
            if checkout['status'] not in (CheckoutStatus.PENDING, CheckoutStatus.RUNNING):
                break
            time.sleep(0.05)
        self.assertEqual(checkout['status'], CheckoutStatus.COMPLETE)
        self.assertEqual(File().load(file['_id'], force=True)['assetstoreId'],
                         self.fsAssetstore['_id'])
        self._threadPatch.start()
