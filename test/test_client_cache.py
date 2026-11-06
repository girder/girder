import io
import os
import unittest.mock

import diskcache_community
import girder_client


class MakeDir:
    """Pickles as a call to os.mkdir, which unpickling the entry would run."""

    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (os.mkdir, (self.path,))


def testDownloadFileSkipsPickledCacheEntry(tmp_path):
    cacheDir = str(tmp_path / 'cache')
    marker = tmp_path / 'ran'
    content = b'downloaded file contents'
    downloads = []

    def streamingFileDownload(fileId):
        downloads.append(fileId)
        return unittest.mock.Mock(headers={}, iter_content=lambda chunk_size: [content])

    client = girder_client.GirderClient(
        apiUrl='http://127.0.0.1:8080/api/v1', cacheSettings={'directory': cacheDir})
    client.getFile = lambda fileId: {'_id': fileId, 'size': len(content), 'created': 'now'}
    client._streamingFileDownload = streamingFileDownload

    def download():
        out = io.BytesIO()
        client.downloadFile('abc', out)
        return out.getvalue()

    assert download() == content
    assert download() == content
    assert downloads == ['abc']

    with diskcache_community.Cache(cacheDir, disk=diskcache_community.Disk) as writer:
        key, = list(writer)
        writer.set(key, MakeDir(str(marker)))

    assert download() == content
    assert downloads == ['abc', 'abc']
    assert not marker.exists()
