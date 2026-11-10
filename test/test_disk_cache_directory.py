import os
import stat
import sys

import girder_client
import pytest

try:
    from girder.cli import mount
except (ImportError, OSError):
    # mfusepy raises OSError when libfuse cannot be loaded
    mount = None


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX permissions')
def testClientCacheDirectoryIsPrivate(tmp_path):
    cacheDir = tmp_path / 'client'
    client = girder_client.GirderClient(
        apiUrl='http://127.0.0.1:8080/api/v1', cacheSettings={'directory': str(cacheDir)})
    assert client.cache.directory == str(cacheDir)
    assert _mode(cacheDir) == 0o700

    # An existing directory is also made private
    cacheDir.chmod(0o755)
    girder_client.GirderClient(
        apiUrl='http://127.0.0.1:8080/api/v1', cacheSettings={'directory': str(cacheDir)})
    assert _mode(cacheDir) == 0o700


@pytest.mark.skipif(sys.platform == 'win32', reason='POSIX permissions')
@pytest.mark.skipif(mount is None, reason='FUSE is not available')
def testMountCacheDirectoryIsPrivate(tmp_path):
    cacheDir = tmp_path / 'mount'
    op = mount.ServerFuse(options={'diskcache_directory': str(cacheDir)})
    assert op.diskcache['cache'].directory == str(cacheDir)
    assert _mode(cacheDir) == 0o700
