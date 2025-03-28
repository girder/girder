import os
import tempfile

import pytest
from girder.models.folder import Folder
from girder.utility import path as path_util
from pytest_girder.assertions import assertStatusOk


@pytest.fixture
def temp_files():
    """Creates temporary .csv, .png, and .jpg files and deletes them after use."""
    temp_dir = tempfile.mkdtemp()
    file_paths = {
        'csv': os.path.join(temp_dir, 'test.csv'),
        'png': os.path.join(temp_dir, 'test.png'),
        'jpg': os.path.join(temp_dir, 'test.jpg'),
    }

    # Create empty files
    for path in file_paths.values():
        with open(path, 'wb') as f:
            f.write(b'')

    yield file_paths

    # Cleanup
    for path in file_paths.values():
        os.remove(path)
    os.rmdir(temp_dir)


def test_mimetype_guessing(server, admin, fsAssetstore, temp_files):
    """Test that the assetstore correctly guesses the mimetype of files."""
    # Upload files

    folder = next(
        Folder().childFolders(
            admin, parentType='user', force=True, filters={'name': 'Public'}
        )
    )

    for key, value in temp_files.items():
        params = {
            'importPath': value,
            'destinationType': 'folder',
            'destinationId': str(folder['_id']),
        }
        resp = server.request(
            path=f'/assetstore/{fsAssetstore["_id"]}/import',
            method='POST',
            user=admin,
            params=params,
        )
        assertStatusOk(resp)
        file = path_util.lookUpPath(
            f'/user/{admin["login"]}/Public/test.{key}/test.{key}', admin
        )['document']

        assert (
            file['mimeType']
            == {
                'csv': 'text/csv',
                'png': 'image/png',
                'jpg': 'image/jpeg',
            }[key]
        )
