import io

from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload
import pytest
from pytest_girder.assertions import assertStatus
from pytest_girder.utils import uploadFile


def testEmptyUploadFromFile(admin, fsAssetstore):
    dest = Folder().childFolders(admin, parentType='user')[0]
    file = Upload().uploadFromFile(io.BytesIO(b''), size=0, name='empty', parent=dest, user=admin)
    assert File().load(file['_id'], force=True) is not None
    assert file['assetstoreId'] == fsAssetstore['_id']


@pytest.mark.parametrize('range,status,cr,cl', (
    ('bytes=0-', 206, 'bytes 0-99/100', 100),
    ('bytes=0-10', 206, 'bytes 0-10/100', 11),
    (None, 200, None, 100)
))
def testRangeRequestBehavior(range, status, cr, cl, admin, server, fsAssetstore):
    dest = Folder().childFolders(admin, parentType='user')[0]
    file = uploadFile('test', b'a' * 100, admin, dest)
    headers = [('Range', range)] if range else []
    resp = server.request(
        path='/file/%s/download' % file['_id'], user=admin, additionalHeaders=headers, isJson=False)
    assertStatus(resp, status)
    assert resp.headers['Content-Length'] == cl
    if cr is None:
        assert 'Content-Range' not in resp.headers
    else:
        assert resp.headers['Content-Range'] == cr
