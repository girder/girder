import girder_client
from unittest import mock
import os
import pytest

from girder_worker_utils.transforms.contrib import girder_io


@pytest.fixture
def mock_gc():
    return mock.MagicMock(spec=girder_client.GirderClient)


@pytest.fixture
def mock_rmtree():
    with mock.patch('shutil.rmtree') as rmtree:
        yield rmtree


def test_GirderFileIdAllowDirect_without_env(mock_gc, mock_rmtree):
    local_path = os.path.abspath(__file__)
    t = girder_io.GirderFileIdAllowDirect('the_id', 'the_name', local_path, gc=mock_gc)
    t.transform()
    mock_gc.downloadFile.assert_called_once()
    assert 'the_id' in mock_gc.downloadFile.call_args[0]
    mock_rmtree.assert_not_called()
    t.cleanup()
    mock_rmtree.assert_called_once()


@mock.patch.dict(os.environ, {'GW_DIRECT_PATHS': 'true'})
def test_GirderFileIdAllowDirect_with_env(mock_gc, mock_rmtree):
    local_path = os.path.abspath(__file__)
    t = girder_io.GirderFileIdAllowDirect('the_id', 'the_name', local_path, gc=mock_gc)
    t.transform()
    mock_gc.downloadFile.assert_not_called()
    t.cleanup()
    mock_rmtree.assert_not_called()


@mock.patch.dict(os.environ, {'GW_DIRECT_PATHS': 'true'})
def test_GirderFileIdAllowDirect_with_env_and_unreachable_file(mock_gc, mock_rmtree):
    t = girder_io.GirderFileIdAllowDirect('the_id', 'the_name', 'the_path', gc=mock_gc)
    t.transform()
    mock_gc.downloadFile.assert_called_once()
    assert 'the_id' in mock_gc.downloadFile.call_args[0]
    mock_rmtree.assert_not_called()
    t.cleanup()
    mock_rmtree.assert_called_once()
