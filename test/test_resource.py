import json

import pytest

from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.token import Token
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def writableFolder(admin, user):
    folder = Folder().createFolder(
        parent=admin, parentType='user', creator=admin, name='writable', public=False)
    Folder().setUserAccess(folder, user, AccessType.WRITE, save=True)
    subfolder = Folder().createFolder(
        parent=folder, parentType='folder', creator=admin, name='sub')
    items = [Item().createItem('item%d' % idx, admin, folder) for idx in range(3)]
    yield {'folder': folder, 'subfolder': subfolder, 'items': items}


def _deleteResources(server, resources, **kwargs):
    return server.request(path='/resource', method='DELETE', params={
        'resources': json.dumps({
            kind: [str(doc['_id']) for doc in docs] for kind, docs in resources.items()})
    }, **kwargs)


def testDeleteItemsWithWriteAccess(server, user, writableFolder):
    resp = _deleteResources(server, {'item': writableFolder['items']}, user=user)
    assertStatusOk(resp)
    assert Item().findOne({'folderId': writableFolder['folder']['_id']}) is None


def testDeleteFolderRequiresAdminAccess(server, user, writableFolder):
    resp = _deleteResources(server, {'folder': [writableFolder['subfolder']]}, user=user)
    assertStatus(resp, 403)
    assert Folder().load(writableFolder['subfolder']['_id'], force=True) is not None


def testDeleteResourcesTokenScope(server, user, writableFolder):
    token = Token().createToken(user=user, scope=TokenScope.DATA_WRITE)
    resp = _deleteResources(
        server, {'folder': [writableFolder['subfolder']]}, token=token)
    assertStatus(resp, 401)
    assert Folder().load(writableFolder['subfolder']['_id'], force=True) is not None

    resp = _deleteResources(server, {'item': writableFolder['items']}, token=token)
    assertStatusOk(resp)
    assert Item().findOne({'folderId': writableFolder['folder']['_id']}) is None
