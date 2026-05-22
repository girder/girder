import os
import stat

import requests

from girder.models.file import File
from girder.models.folder import Folder
from pytest_girder.utils import uploadFile


def test_download_unreadable_file(asgiBoundServer, admin, fsAssetstore):
    dest = Folder().childFolders(admin, parentType='user')[0]
    test_file = uploadFile('test.txt', b'content', admin, dest)
    file = File().load(test_file['_id'], force=True)
    adapter = File().getAssetstoreAdapter(file)
    path = adapter.getLocalFilePath(file)
    original_mode = os.stat(path).st_mode
    try:
        os.chmod(path, original_mode & ~stat.S_IROTH & ~stat.S_IRGRP & ~stat.S_IRUSR)
        resp = requests.get(
            f'http://127.0.0.1:{asgiBoundServer.boundPort}/api/v1/file/{file["_id"]}/download',
        )
    finally:
        os.chmod(path, original_mode)
    assert resp.status_code == 500
    assert int(resp.headers['Content-Length']) > 10
