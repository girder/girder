import os

import girder_client
from unittest import mock
import pytest

from girder_worker_utils.transforms import girder_io

DIR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_dir')
FILE_PATH = os.path.join(DIR_PATH, 'file1.txt')


@pytest.fixture
def mock_gc():
    return mock.MagicMock(spec=girder_client.GirderClient)


@pytest.fixture
def mock_rm():
    with mock.patch('os.remove') as rm:
        yield rm


@pytest.fixture
def mock_rmtree():
    with mock.patch('shutil.rmtree') as rmtree:
        yield rmtree


def test_GirderUploadToItem_with_kwargs(mock_gc):
    uti = girder_io.GirderUploadToItem('the_id', gc=mock_gc, upload_kwargs={'reference': 'foo'})
    assert uti.transform(FILE_PATH) == 'the_id'
    mock_gc.uploadFileToItem.assert_called_once_with('the_id', FILE_PATH, reference='foo')


def test_GirderUploadToItem_upload_directory(mock_gc):
    uti = girder_io.GirderUploadToItem('the_id', gc=mock_gc, upload_kwargs={'reference': 'foo'})
    assert uti.transform(DIR_PATH) == 'the_id'

    files = {'file1.txt', 'file2.txt'}
    calls = [mock.call('the_id', os.path.join(DIR_PATH, f), reference='foo') for f in files]
    mock_gc.uploadFileToItem.assert_has_calls(calls, any_order=True)


def test_GirderUploadToFolder_upload_file(mock_gc):
    utf = girder_io.GirderUploadToFolder('the_id', gc=mock_gc, upload_kwargs={'reference': 'foo'})
    assert utf.transform(FILE_PATH) == 'the_id'
    mock_gc.uploadFileToFolder.assert_any_call('the_id', FILE_PATH, reference='foo')


def test_GirderUploadToFolder_upload_directory(mock_gc):
    mock_gc.createFolder.return_value = {'_id': 'sub_id'}
    utf = girder_io.GirderUploadToFolder('the_id', gc=mock_gc, upload_kwargs={'reference': 'foo'})
    assert utf.transform(DIR_PATH) == 'the_id'

    files = {'file1.txt', 'file2.txt'}
    calls = [mock.call('the_id', os.path.join(DIR_PATH, f), reference='foo') for f in files]
    calls.append(mock.call(
        'sub_id', os.path.join(DIR_PATH, 'subdir', 'file3.txt'), reference='foo'))
    mock_gc.uploadFileToFolder.assert_has_calls(calls, any_order=True)


@pytest.mark.parametrize('should_delete', (True, False))
def test_GirderUploadToItem_cleanup_file(mock_gc, mock_rm, mock_rmtree, should_delete):
    uti = girder_io.GirderUploadToItem('the_id', delete_file=should_delete, gc=mock_gc)
    uti.transform(FILE_PATH)
    uti.cleanup()
    if should_delete:
        mock_rm.assert_called_once_with(FILE_PATH)
    else:
        mock_rm.assert_not_called()
    mock_rmtree.assert_not_called()


@pytest.mark.parametrize('should_delete', (True, False))
@pytest.mark.parametrize('obj', (girder_io.GirderUploadToFolder, girder_io.GirderUploadToItem))
def test_GirderUploadToResource_cleanup_dir(mock_gc, mock_rm, mock_rmtree, should_delete, obj):
    uti = obj('the_id', delete_file=should_delete, gc=mock_gc)
    uti.transform(DIR_PATH)
    uti.cleanup()
    if should_delete:
        mock_rmtree.assert_called_once_with(DIR_PATH)
    else:
        mock_rmtree.assert_not_called()
    mock_rm.assert_not_called()


def test_GirderUploadJobArtifact(mock_gc):
    t = girder_io.GirderUploadJobArtifact(job_id='123', name='hello', gc=mock_gc)
    t.transform(FILE_PATH)
    mock_gc.post.assert_called_once()
    url = mock_gc.post.call_args[0][0]
    assert 'job/123/artifact?' in url
    assert 'name=hello' in url

    mock_gc.reset_mock()
    t.transform(DIR_PATH)
    assert mock_gc.post.call_count == 2
    urls = sorted(args[0][0] for args in mock_gc.post.call_args_list)
    assert 'name=file1.txt' in urls[0]
    assert 'name=file2.txt' in urls[1]


def test_GirderFileId(mock_gc, mock_rmtree):
    t = girder_io.GirderFileId(_id='the_id', gc=mock_gc)
    t.transform()
    mock_gc.downloadFile.assert_called_once()
    assert 'the_id' in mock_gc.downloadFile.call_args[0]
    mock_rmtree.assert_not_called()
    t.cleanup()
    mock_rmtree.assert_called_once()


def test_GirderItemId(mock_gc, mock_rmtree):
    t = girder_io.GirderItemId(_id='the_id', gc=mock_gc)
    t.transform()
    mock_gc.downloadItem.assert_called_once()
    assert 'the_id' in mock_gc.downloadItem.call_args[0]
    mock_rmtree.assert_not_called()
    t.cleanup()
    mock_rmtree.assert_called_once()
