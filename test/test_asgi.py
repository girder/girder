import os
import stat
import time

import psutil
import requests
from requests.adapters import HTTPAdapter

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


def test_large_file_download_memory_consumption(asgiBoundServer, admin, fsAssetstore):

    file_size_mb = 100
    large_content = b'x' * (file_size_mb * 1024 * 1024)
    dest = Folder().childFolders(admin, parentType='user')[0]
    uploaded_file = uploadFile('large_file.bin', large_content, admin, dest)
    file_id = uploaded_file['_id']
    # Monitor memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    # Download file with small chunk size
    download_url = (
        f'http://127.0.0.1:{asgiBoundServer.boundPort}/api/v1/file/{file_id}/download')
    # Use throttled connection to force chunked streaming
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=1,
        pool_maxsize=1,
        max_retries=0,
    )
    session.mount('http://', adapter)
    chunk_size = 8192
    response = session.get(download_url, stream=True, params={
        'chunkSize': chunk_size
    })
    response.raise_for_status()
    memory_usage = []
    download_start = time.time()
    for chunk in response.iter_content(chunk_size):
        if chunk:
            current_memory = process.memory_info().rss
            memory_usage.append(current_memory)
            if len(memory_usage) > 100:
                break
            time.sleep(0.1)
    download_time = time.time() - download_start
    max_memory = max(memory_usage) if memory_usage else initial_memory
    memory_increase = (max_memory - initial_memory) / 1024 / 1024
    max_allowed_increase = 10  # MB
    assert memory_increase < max_allowed_increase, (
        f'Memory increase of {memory_increase:.2f}MB exceeds limit of '
        f'{max_allowed_increase}MB. Download likely buffered entirely in memory.'
    )
    assert len(memory_usage) > 10, 'Insufficient memory samples'
    assert download_time > 0.5, 'Download too fast, may not have been throttled'
