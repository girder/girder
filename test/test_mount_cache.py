import io
import os
import unittest.mock

import diskcache_community
import pytest

from girder.exceptions import FilePathException

try:
    from girder.cli import mount
except OSError:
    # mfusepy raises OSError when libfuse cannot be loaded
    pytest.skip('libfuse is not available', allow_module_level=True)


class MakeDir:
    """Pickles as a call to os.mkdir, which unpickling the entry would run."""

    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (os.mkdir, (self.path,))


def testReadSkipsPickledDiskCacheEntry(tmp_path):
    cacheDir = str(tmp_path / 'cache')
    marker = tmp_path / 'ran'
    content = b'chunk from a remote assetstore'
    doc = {'_id': 'abc', 'size': len(content), 'created': 'now'}

    class RemoteFile:
        def getAssetstoreAdapter(self, doc):
            return self

        def getLocalFilePath(self, doc):
            raise FilePathException('no local path')

        def open(self, doc):
            return io.BytesIO(content)

    op = mount.ServerFuse(options={'diskcache_directory': cacheDir})
    op._get_path = lambda path: {'model': 'file', 'document': doc}
    with unittest.mock.patch.object(mount, 'File', RemoteFile):
        fh = op.open('/file', os.O_RDONLY)
        assert op.read('/file', 100, 0, fh) == content
        assert op.read('/file', 100, 0, fh) == content
        assert (op.diskcache['miss'], op.diskcache['hits']) == (1, 1)

        with diskcache_community.Cache(cacheDir, disk=diskcache_community.Disk) as writer:
            key, = list(writer)
            writer.set(key, MakeDir(str(marker)))

        assert op.read('/file', 100, 0, fh) == content
        assert (op.diskcache['miss'], op.diskcache['hits']) == (2, 1)
    assert not marker.exists()
