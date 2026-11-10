import socket

import pytest

from girder.constants import AssetstoreType
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def unreachableS3Assetstore(db):
    # Find a local port with nothing listening on it so that connections to
    # the S3 endpoint are refused.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    # Save without validation, since validation would try to reach the server.
    yield Assetstore().save({
        'type': AssetstoreType.S3,
        'name': 'Unreachable S3',
        'bucket': 'bucketname',
        'prefix': 'prefix',
        'accessKeyId': 'abc',
        'secret': '123',
        'service': 'http://127.0.0.1:%d' % port,
        'readOnly': False,
        'current': False,
    }, validate=False)


def testDeleteUnreachableEmptyAssetstore(server, admin, fsAssetstore, unreachableS3Assetstore):
    resp = server.request(
        path='/assetstore/%s' % unreachableS3Assetstore['_id'], method='DELETE', user=admin)
    assertStatusOk(resp)
    assert resp.json['message'] == 'Deleted assetstore Unreachable S3.'
    assert Assetstore().load(unreachableS3Assetstore['_id']) is None


def testDeleteUnreachableAssetstoreWithFiles(
        server, admin, fsAssetstore, unreachableS3Assetstore):
    folder = next(Folder().childFolders(admin, 'user', user=admin))
    item = Item().createItem(name='x.txt', creator=admin, folder=folder)
    File().createFile(
        creator=admin, item=item, name='x.txt', size=1,
        assetstore=unreachableS3Assetstore, mimeType='text/plain')

    resp = server.request(
        path='/assetstore/%s' % unreachableS3Assetstore['_id'], method='DELETE', user=admin)
    assertStatus(resp, 400)
    assert resp.json['message'] == 'You may not delete an assetstore that contains files.'
    assert Assetstore().load(unreachableS3Assetstore['_id']) is not None
