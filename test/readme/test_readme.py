import os
import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk
from girder.models.folder import Folder


@pytest.fixture
def privateFolder(admin, fsAssetstore):
    folders = Folder().childFolders(
        parent=admin, parentType='user', user=admin
    )
    for folder in folders:
        if folder['public'] is False:
            return folder


def readmeContents(readmeName):
    path = os.path.join(
        os.path.dirname(__file__), 'data', readmeName,
    )
    with open(path, 'rb') as file:
        return file.read()


@pytest.mark.parametrize('readmeName', [
    'README',
    'README.md',
    'README.txt',
])
@pytest.mark.plugin('readme')
def testReadme(server, admin, user, privateFolder, readmeName):
    contents = readmeContents(readmeName)

    # Upload the README to the admin's private folder
    resp = server.request(
        path='/file',
        method='POST',
        user=admin,
        params={
            'parentType': 'folder',
            'parentId': privateFolder['_id'],
            'name': readmeName,
            'size': len(contents),
        },
    )
    assertStatusOk(resp)
    uploadId = resp.json['_id']

    # Upload the contents of the README
    resp = server.request(
        path='/file/chunk',
        method='POST',
        user=admin,
        body=contents,
        params={'uploadId': uploadId},
        type='text/plain',
    )
    assertStatusOk(resp)

    # Verify that the readme endpoint returns the correct response for admin
    resp = server.request(
        path=f'/folder/{privateFolder["_id"]}/readme',
        method='GET',
        user=admin,
        isJson=False,
    )
    assertStatusOk(resp)
    readme = b''
    for b in resp.body:
        readme += b
    assert contents == readme

    # Verify that the readme endpoint returns 403 Forbidden for user
    resp = server.request(
        path=f'/folder/{privateFolder["_id"]}/readme',
        method='GET',
        user=user,
        isJson=False,
    )
    assertStatus(resp, 403)


@pytest.mark.plugin('readme')
def testNoReadme(server, admin, privateFolder):
    # Verify that the readme endpoint returns 204 No Content when there is no README
    resp = server.request(
        path=f'/folder/{privateFolder["_id"]}/readme',
        method='GET',
        user=admin,
        isJson=False,
    )
    assertStatus(resp, 204)
