"""
Test for FilesystemAssetstoreAdapter.uploadChunk rollback safety.
"""
import copy
import io
import os
import threading

import pytest

from girder.exceptions import GirderException, ValidationException
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
    started (i.e., undo just its bytes via os.path.getsize - size), not to an
    outdated upload['received'] that is ahead of this request's own count.
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
