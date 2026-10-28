import datetime
import io
import logging
import os
import socket

import boto3
import botocore.exceptions
import pytest
from girder_local_checkout import utils
from girder_local_checkout.models import Checkout, CheckoutFile, CheckoutStatus
from girder_local_checkout.settings import PluginSettings
from moto.server import ThreadedMotoServer

from girder.constants import AccessType
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.utility.s3_assetstore_adapter import S3AssetstoreAdapter, makeBotoConnectParams
from pytest_girder.assertions import assertStatus, assertStatusOk

BUCKET = 'bucketname'
ACCESS_KEY = 'abc'
SECRET = '123'


@pytest.fixture
def s3Server():
    """Run a mock S3 server for the duration of a test."""
    # The latest moto/boto/botocore requires dummy credentials to function
    os.environ.setdefault('AWS_ACCESS_KEY_ID', ACCESS_KEY)
    os.environ.setdefault('AWS_SECRET_ACCESS_KEY', SECRET)
    logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = ThreadedMotoServer(ip_address='127.0.0.1', port=port, verbose=False)
    server.start()
    # Use small chunks so that multipart uploads are exercised quickly
    chunkLen = S3AssetstoreAdapter.CHUNK_LEN
    S3AssetstoreAdapter.CHUNK_LEN = 1024 * 1024 * 5
    yield 'http://127.0.0.1:%d' % port
    S3AssetstoreAdapter.CHUNK_LEN = chunkLen
    server.stop()


@pytest.fixture
def s3Client(s3Server):
    """A boto client with the test bucket created."""
    client = boto3.client('s3', **makeBotoConnectParams(ACCESS_KEY, SECRET, s3Server))
    client.create_bucket(ACL='private', Bucket=BUCKET)
    yield client
    # Empty the bucket so that each test starts fresh
    for obj in client.list_objects_v2(Bucket=BUCKET).get('Contents', []):
        client.delete_object(Bucket=BUCKET, Key=obj['Key'])
    client.delete_bucket(Bucket=BUCKET)


@pytest.fixture
def s3Assetstore(db, fsAssetstore, s3Server, s3Client):
    """An S3 assetstore; the filesystem assetstore remains the current one."""
    return Assetstore().createS3Assetstore(
        name='s3', bucket=BUCKET, accessKeyId=ACCESS_KEY, secret=SECRET,
        service=s3Server, prefix='test')


@pytest.fixture
def folder(admin):
    return Folder().findOne(
        {'parentId': admin['_id'], 'parentCollection': 'user', 'name': 'Private'})


def uploadToS3(folder, name, data, admin, s3Assetstore):
    return Upload().uploadFromFile(
        io.BytesIO(data), len(data), name, parentType='folder', parent=folder,
        user=admin, assetstore=s3Assetstore)


def download(server, file, admin):
    """Read a file's data as the server would stream it (e.g. in a zip)."""
    file = File().load(file['_id'], force=True)
    return b''.join(File().download(file, headers=False)())


def s3KeyExists(s3Client, key):
    try:
        s3Client.head_object(Bucket=BUCKET, Key=key)
        return True
    except botocore.exceptions.ClientError:
        return False


def localPath(fsAssetstore, file):
    return os.path.join(fsAssetstore['root'], file['path'])


@pytest.mark.plugin('local_checkout')
def testCheckoutAndRelease(server, admin, fsAssetstore, s3Assetstore, s3Client, folder,
                           eagerWorkerTasks):
    sub = Folder().createFolder(folder, 'sub', creator=admin)
    data1 = b'hello world' * 1000
    data2 = os.urandom(6 * 1024 * 1024)
    file1 = uploadToS3(folder, 'one.txt', data1, admin, s3Assetstore)
    file2 = uploadToS3(sub, 'two.bin', data2, admin, s3Assetstore)
    # An empty file and a file already on the filesystem are counted but not copied
    uploadToS3(folder, 'empty.txt', b'', admin, s3Assetstore)
    fsFile = Upload().uploadFromFile(
        io.BytesIO(b'local'), 5, 'local.txt', parentType='folder', parent=folder,
        user=admin, assetstore=fsAssetstore)
    s3Key1 = file1['s3Key']

    resp = server.request(path='/folder/%s/local_checkout' % folder['_id'], user=admin)
    assertStatusOk(resp)
    assert resp.json['checkout'] is None
    assert resp.json['enabled'] is True
    assert resp.json['assetstoreName'] == fsAssetstore['name']
    assert resp.json['fileCount'] == 3
    assert resp.json['localCount'] == 0
    assert resp.json['bytes'] == len(data1) + len(data2)

    resp = server.request(
        path='/folder/%s/local_checkout' % folder['_id'], method='PUT', user=admin,
        params={'days': 5})
    assertStatusOk(resp)
    checkout = Checkout().load(resp.json['_id'])
    assert checkout['status'] == CheckoutStatus.COMPLETE
    assert checkout['fileCount'] == 3
    assert checkout['localCount'] == 3
    assert checkout['bytes'] == len(data1) + len(data2)
    assert checkout['days'] == 5

    for file, data in ((file1, data1), (file2, data2)):
        file = File().load(file['_id'], force=True)
        assert file['assetstoreId'] == fsAssetstore['_id']
        assert 's3Key' not in file
        assert 'relpath' not in file
        assert os.path.getsize(localPath(fsAssetstore, file)) == len(data)
        assert download(server, file, admin) == data
        record = CheckoutFile().findByFile(file)
        assert record['original']['s3Key']
        assert record['expires'] == checkout['expires']
    assert File().load(fsFile['_id'], force=True)['path'] == fsFile['path']
    # The original S3 data is retained
    assert s3KeyExists(s3Client, s3Key1)

    resp = server.request(path='/folder/%s/local_checkout' % folder['_id'], user=admin)
    assertStatusOk(resp)
    assert resp.json['checkout']['status'] == CheckoutStatus.COMPLETE
    assert resp.json['localCount'] == 3
    assert resp.json['localBytes'] == len(data1) + len(data2)

    resp = server.request(path='/local_checkout', user=admin)
    assertStatusOk(resp)
    assert len(resp.json['checkouts']) == 1
    assert resp.json['checkouts'][0]['folderPath'] == '/user/admin/Private'
    assert resp.json['checkouts'][0]['userLogin'] == 'admin'
    assert resp.json['localFileCount'] == 3
    assert resp.json['localBytes'] == len(data1) + len(data2)
    assert resp.json['assetstore']['name'] == fsAssetstore['name']

    # Release
    localFile1 = File().load(file1['_id'], force=True)
    resp = server.request(
        path='/folder/%s/local_checkout' % folder['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assert resp.json['released'] is True
    assert Checkout().findByFolder(folder) is None
    assert CheckoutFile().find().count() == 0
    assert not os.path.exists(localPath(fsAssetstore, localFile1))
    file1 = File().load(file1['_id'], force=True)
    assert file1['assetstoreId'] == s3Assetstore['_id']
    assert file1['s3Key'] == s3Key1
    assert 'path' not in file1
    assert download(server, file1, admin) == data1

    resp = server.request(
        path='/folder/%s/local_checkout' % folder['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assert resp.json['released'] is False


@pytest.mark.plugin('local_checkout')
def testDurationChangesAndExpiry(server, admin, fsAssetstore, s3Assetstore, folder,
                                 eagerWorkerTasks):
    file = uploadToS3(folder, 'one.txt', b'data', admin, s3Assetstore)
    sub = Folder().createFolder(folder, 'sub', creator=admin)
    subFile = uploadToS3(sub, 'two.txt', b'more data', admin, s3Assetstore)

    def put(fold, days):
        resp = server.request(
            path='/folder/%s/local_checkout' % fold['_id'], method='PUT', user=admin,
            params={'days': days})
        assertStatusOk(resp)
        return resp.json

    # The subfolder is checked out longer than its parent
    put(sub, 10)
    put(folder, 3)
    subCheckout = Checkout().findByFolder(sub)
    folderCheckout = Checkout().findByFolder(folder)
    fileRecord = CheckoutFile().findByFile(file)
    subRecord = CheckoutFile().findByFile(subFile)
    assert fileRecord['expires'] == folderCheckout['expires']
    assert subRecord['expires'] == subCheckout['expires']
    assert set(subRecord['checkoutIds']) == {subCheckout['_id'], folderCheckout['_id']}

    # Extending the parent beyond the subfolder extends the subfolder's file
    put(folder, 20)
    folderCheckout = Checkout().findByFolder(folder)
    assert CheckoutFile().findByFile(subFile)['expires'] == folderCheckout['expires']
    # Shortening it again falls back to the subfolder's checkout
    put(folder, 1)
    assert CheckoutFile().findByFile(subFile)['expires'] == subCheckout['expires']

    # Releasing the parent keeps the subfolder's file local
    put(folder, 0)
    assert Checkout().findByFolder(folder) is None
    assert CheckoutFile().findByFile(file) is None
    assert File().load(file['_id'], force=True)['assetstoreId'] == s3Assetstore['_id']
    assert CheckoutFile().findByFile(subFile)['checkoutIds'] == [subCheckout['_id']]
    assert File().load(subFile['_id'], force=True)['assetstoreId'] == fsAssetstore['_id']

    # Cleanup does nothing until the checkout expires
    resp = server.request(path='/local_checkout/cleanup', method='POST', user=admin)
    assertStatusOk(resp)
    assert resp.json['released'] == 0
    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    Checkout().update({'_id': subCheckout['_id']}, {'$set': {'expires': past}})
    CheckoutFile().update({'_id': subRecord['_id']}, {'$set': {'expires': past}})
    resp = server.request(path='/local_checkout/cleanup', method='POST', user=admin)
    assertStatusOk(resp)
    assert resp.json['released'] == 1
    assert Checkout().findByFolder(sub) is None
    assert CheckoutFile().findByFile(subFile) is None
    assert File().load(subFile['_id'], force=True)['assetstoreId'] == s3Assetstore['_id']
    assert download(server, subFile, admin) == b'more data'


@pytest.mark.plugin('local_checkout')
def testFileDeletionAndReplacement(server, admin, fsAssetstore, s3Assetstore, s3Client, folder,
                                   eagerWorkerTasks):
    file1 = uploadToS3(folder, 'one.txt', b'data one', admin, s3Assetstore)
    file2 = uploadToS3(folder, 'two.txt', b'data two', admin, s3Assetstore)
    resp = server.request(
        path='/folder/%s/local_checkout' % folder['_id'], method='PUT', user=admin,
        params={'days': 5})
    assertStatusOk(resp)
    localFile1 = File().load(file1['_id'], force=True)

    # Deleting a checked-out file removes the local copy and the S3 original
    resp = server.request(path='/file/%s' % file1['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assert CheckoutFile().findByFile(file1) is None
    assert not os.path.exists(localPath(fsAssetstore, localFile1))
    assert not s3KeyExists(s3Client, file1['s3Key'])

    # Replacing the contents of a checked-out file likewise drops the original
    upload = Upload().createUploadToFile(
        File().load(file2['_id'], force=True), admin, 12, assetstore=fsAssetstore)
    Upload().handleChunk(upload, io.BytesIO(b'new contents'))
    assert CheckoutFile().findByFile(file2) is None
    assert not s3KeyExists(s3Client, file2['s3Key'])
    assert download(server, file2, admin) == b'new contents'
    checkout = Checkout().findByFolder(folder)
    assert checkout is not None

    # Deleting the folder removes the checkout
    resp = server.request(path='/folder/%s' % folder['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assert Checkout().findByFolder(folder) is None


@pytest.mark.plugin('local_checkout')
def testInsufficientSpace(server, admin, fsAssetstore, s3Assetstore, folder, eagerWorkerTasks,
                          monkeypatch):
    folderA = Folder().createFolder(folder, 'A', creator=admin)
    folderB = Folder().createFolder(folder, 'B', creator=admin)
    fileA = uploadToS3(folderA, 'a.txt', b'a' * 100, admin, s3Assetstore)
    fileB = uploadToS3(folderB, 'b.txt', b'b' * 100, admin, s3Assetstore)

    # Pretend the assetstore only has room for one of the files
    def freeSpace(adapter):
        return 150 - sum(record['size'] for record in CheckoutFile().find())

    monkeypatch.setattr(utils, 'freeSpace', freeSpace)

    resp = server.request(
        path='/folder/%s/local_checkout' % folderA['_id'], method='PUT', user=admin,
        params={'days': 2})
    assertStatusOk(resp)
    assert Checkout().findByFolder(folderA)['status'] == CheckoutStatus.COMPLETE
    assert CheckoutFile().findByFile(fileA) is not None

    # A longer checkout evicts the shorter one when space runs out
    resp = server.request(
        path='/folder/%s/local_checkout' % folderB['_id'], method='PUT', user=admin,
        params={'days': 10})
    assertStatusOk(resp)
    assert Checkout().findByFolder(folderB)['status'] == CheckoutStatus.COMPLETE
    assert CheckoutFile().findByFile(fileB) is not None
    assert CheckoutFile().findByFile(fileA) is None
    assert File().load(fileA['_id'], force=True)['assetstoreId'] == s3Assetstore['_id']
    checkoutA = Checkout().findByFolder(folderA)
    assert checkoutA['status'] == CheckoutStatus.PARTIAL
    assert checkoutA['localCount'] == 0

    # A shorter checkout cannot evict the longer one and is left partial
    resp = server.request(
        path='/folder/%s/local_checkout' % folderA['_id'], method='PUT', user=admin,
        params={'days': 3})
    assertStatusOk(resp)
    checkoutA = Checkout().findByFolder(folderA)
    assert checkoutA['status'] == CheckoutStatus.PARTIAL
    assert 'Insufficient space' in checkoutA['message']
    assert CheckoutFile().findByFile(fileA) is None
    assert CheckoutFile().findByFile(fileB) is not None

    # An upload to the filesystem assetstore evicts checkouts of any duration
    # rather than failing
    uploaded = Upload().uploadFromFile(
        io.BytesIO(b'c' * 100), 100, 'c.txt', parentType='folder', parent=folder,
        user=admin, assetstore=fsAssetstore)
    assert uploaded['assetstoreId'] == fsAssetstore['_id']
    assert download(server, uploaded, admin) == b'c' * 100
    assert CheckoutFile().findByFile(fileB) is None
    assert File().load(fileB['_id'], force=True)['assetstoreId'] == s3Assetstore['_id']
    assert Checkout().findByFolder(folderB)['status'] == CheckoutStatus.PARTIAL
    assert download(server, fileB, admin) == b'b' * 100


@pytest.mark.plugin('local_checkout')
def testPermissionsAndSettings(server, admin, user, fsAssetstore, s3Assetstore, folder,
                               eagerWorkerTasks):
    uploadToS3(folder, 'one.txt', b'data', admin, s3Assetstore)
    Folder().setUserAccess(folder, user, level=AccessType.WRITE, save=True)
    path = '/folder/%s/local_checkout' % folder['_id']

    resp = server.request(path=path, method='PUT', user=user, params={'days': 1000})
    assertStatus(resp, 400)
    assert 'may not exceed' in resp.json['message']

    Setting().set(PluginSettings.ADMIN_ONLY, True)
    resp = server.request(path=path, method='PUT', user=user, params={'days': 1})
    assertStatus(resp, 403)
    resp = server.request(path=path, user=user)
    assertStatusOk(resp)
    assert resp.json['adminOnly'] is True
    Setting().set(PluginSettings.ADMIN_ONLY, False)

    resp = server.request(path='/local_checkout', user=user)
    assertStatus(resp, 403)

    # Point the plugin at the S3 assetstore: not allowed
    with pytest.raises(Exception):
        Setting().set(PluginSettings.ASSETSTORE_ID, str(s3Assetstore['_id']))
    Setting().set(PluginSettings.ASSETSTORE_ID, str(fsAssetstore['_id']))
    assert utils.getTargetAssetstore()['_id'] == fsAssetstore['_id']
    Setting().set(PluginSettings.ASSETSTORE_ID, '')

    # With an S3 assetstore as the default, the feature is disabled
    Assetstore().update({'_id': fsAssetstore['_id']}, {'$set': {'current': False}})
    Assetstore().update({'_id': s3Assetstore['_id']}, {'$set': {'current': True}})
    resp = server.request(path=path, user=user)
    assertStatusOk(resp)
    assert resp.json['enabled'] is False
    resp = server.request(path=path, method='PUT', user=user, params={'days': 1})
    assertStatus(resp, 400)
    assert 'No filesystem assetstore' in resp.json['message']
    Assetstore().update({'_id': s3Assetstore['_id']}, {'$set': {'current': False}})
    Assetstore().update({'_id': fsAssetstore['_id']}, {'$set': {'current': True}})

    resp = server.request(path=path, method='PUT', user=user, params={'days': 1})
    assertStatusOk(resp)
    assert resp.json['userId'] == str(user['_id'])
    assert Checkout().findByFolder(folder)['status'] == CheckoutStatus.COMPLETE
