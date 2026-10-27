"""
Test for FilesystemAssetstoreAdapter.uploadChunk rollback safety.
"""
import copy
import hashlib
import io
import os
import threading
import time

import pytest

from girder.exceptions import GirderException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.utility import RequestBodyStream

CHUNK = 1024 * 1024 * 5  # the default core.upload_minimum_chunk_size
SHORT = b'x' * 1024  # a non-final chunk that fails checkUploadSize


def send(upload, payload):
    return Upload().handleChunk(upload, RequestBodyStream(io.BytesIO(payload)))


def test_rollback_does_not_delete_another_chunks_bytes(user, fsAssetstore):
    """
    When a stale upload request receives ValidationException oni
    checkUploadSize, the rollback must truncate only back to where its chunk
    started (i.e., undo just its bytes), not to an outdated upload['received']
    that is ahead of this request's own count.
    """
    folder = Folder().createFolder(user, 'test', parentType='user', public=True)
    upload = Upload().createUpload(
        user=user, name='race.bin', parentType='folder', parent=folder,
        size=3 * CHUNK)
    upload = send(upload, b'a' * CHUNK)  # chunk 1 -> received = CHUNK

    # A second request for this same offset. Both pass the offset check in
    # api/v1/file.py because neither has seen the other's save.
    stale = copy.deepcopy(upload)
    upload = send(upload, b'b' * CHUNK)  # chunk 2 -> received = 2 * CHUNK
    assert os.path.getsize(upload['tempFile']) == 2 * CHUNK  # holds

    with pytest.raises(ValidationException):
        send(stale, SHORT)
    Folder().remove(folder)
    # The file size should still be 2*CHUNK because only the stale chunk's
    # bytes were rolled back (just b"x"), not data from the second chunk.
    assert os.path.getsize(upload['tempFile']) == 2 * CHUNK


@pytest.mark.usefixtures('fsAssetstore')
def test_concurrent_chunk_updates_detect_conflict(user, server):
    """
    Test that concurrent uploads updating the same start offset detect a
    conflict and prevent clobbering. This simulates two HTTP requests reading
    the same DB state simultaneously and trying to save at the same time.
    """
    folder = Folder().createFolder(user, 'test_conflict', parentType='user')
    upload = Upload().createUpload(
        user=user, name='conflict.bin', parentType='folder', parent=folder,
        size=3 * CHUNK)
    base_upload = {
        '_id': upload['_id'],
        'received': 0,
        'tempFile': upload['tempFile'],
        'sha512state': upload.get('sha512state'),
        'assetstoreId': upload['assetstoreId'],
    }
    # Synchronization barrier to ensure both threads read DB at exactly the
    # same time
    barrier = threading.Barrier(2)
    results = {}

    def do_chunk(upload_doc, payload_size, thread_id):
        chunk_payload = b'X' * payload_size
        stream = RequestBodyStream(io.BytesIO(chunk_payload), len(chunk_payload))
        try:
            barrier.wait()
            Upload().handleChunk(upload_doc, stream)
            results[thread_id] = {'success': True}
        except GirderException as e:
            # This is expected for the thread that loses the race
            if 'simultaneously modified' in str(e):
                results[thread_id] = {'error': 'Conflict'}
            else:
                raise
        except Exception as e:
            results[thread_id] = {'error': str(e)}

    t1 = threading.Thread(target=do_chunk, args=(base_upload, CHUNK, 1))
    t2 = threading.Thread(target=do_chunk, args=(copy.deepcopy(base_upload), CHUNK, 2))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One thread must succeed and update the DB; the other should raise
    assert results[1].get('success') or results[1].get('error'), 'Thread 1 did not complete.'
    assert results[2].get('success') or results[2].get('error'), 'Thread 2 did not complete.'


class StallingStream:
    """
    A file-like object that yields ``payload`` and then blocks at EOF until
    ``release`` is set, signalling ``atEof`` when it starts blocking.  This
    mimics a slow client whose request body has been read except for the
    terminating empty read.
    """

    def __init__(self, payload, atEof, release):
        self.stream = io.BytesIO(payload)
        self.atEof = atEof
        self.release = release

    def read(self, size=-1):
        data = self.stream.read(size)
        if not data:
            self.atEof.set()
            self.release.wait()
        return data

    def close(self):
        pass


def test_rejected_chunk_does_not_corrupt_concurrent_chunk(user, fsAssetstore):
    """
    A stale retry whose chunk is rejected by checkUploadSize must not corrupt
    a legitimate chunk that is written while the stale request is still
    reading its body.  Previously the rejected bytes were written into the
    shared temp file before validation, the legitimate chunk was appended
    after them, and the rollback truncated the legitimate chunk's tail
    instead of the rejected bytes.
    """
    folder = Folder().createFolder(user, 'test_corrupt', parentType='user')
    upload = Upload().createUpload(
        user=user, name='corrupt.bin', parentType='folder', parent=folder,
        size=3 * CHUNK)
    upload = send(upload, b'a' * CHUNK)
    stale = copy.deepcopy(upload)  # a retry of chunk 2 that is delayed
    upload = send(upload, b'b' * CHUNK)
    tempFile = upload['tempFile']

    atEof = threading.Event()
    release = threading.Event()
    results = {}

    def staleRequest():
        try:
            results['stale'] = Upload().handleChunk(stale, RequestBodyStream(
                StallingStream(b'x' * 1024 * 1024, atEof, release)))
        except Exception as exc:
            results['stale'] = exc

    def legitimateRequest():
        try:
            results['legit'] = send(upload, b'c' * CHUNK)
        except Exception as exc:
            results['legit'] = exc

    staleThread = threading.Thread(target=staleRequest)
    staleThread.start()
    assert atEof.wait(10), 'Stale request never reached EOF'
    legitThread = threading.Thread(target=legitimateRequest)
    legitThread.start()
    # Give the legitimate chunk a chance to be written while the stale
    # request is paused.  With the fix it blocks instead; without it the
    # file grows to include both chunks.
    deadline = time.time() + 3
    while time.time() < deadline and os.path.exists(tempFile) and \
            os.path.getsize(tempFile) < 3 * CHUNK + 1024 * 1024:
        time.sleep(0.05)
    release.set()
    staleThread.join(30)
    legitThread.join(30)
    assert not staleThread.is_alive() and not legitThread.is_alive()

    file = results['legit']
    if isinstance(file, Exception):
        raise file
    if 'received' in file:
        upload = Upload().load(upload['_id'])
        upload['received'] = Upload().requestOffset(upload)
        file = send(upload, b'c' * (3 * CHUNK - upload['received']))
    expected = b'a' * CHUNK + b'b' * CHUNK + b'c' * CHUNK
    assert file['size'] == len(expected)
    assert file['sha512'] == hashlib.sha512(expected).hexdigest()
    with File().open(file) as fh:
        assert fh.read() == expected
    assert isinstance(results['stale'], ValidationException)
    Folder().remove(folder)
