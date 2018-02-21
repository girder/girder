import pytest

from girder.constants import SortDir
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.item import Item


@pytest.fixture
def vfolder(admin):
    folder = Folder().createFolder(admin, 'virtual', parentType='user', virtual=True)
    yield folder


@pytest.fixture
def realFolder(admin):
    realParent = Folder().createFolder(admin, 'x', creator=admin, parentType='user')

    for i in range(10):
        subfolder = Folder().createFolder(realParent, str(i), creator=admin, description='foo')
        item = Item().createItem('item' + str(i), creator=admin, folder=subfolder)
        Item().setMetadata(item, {
            'someVal': i
        })

    yield realParent


def testCannotCreateUnderVirtualFolder(admin, vfolder):
    with pytest.raises(ValidationException) as exc:
        Item().createItem('x', creator=admin, folder=vfolder)
    assert str(exc.value) == 'You cannot save an item underneath a virtual folder.'

    with pytest.raises(ValidationException) as exc:
        Folder().createFolder(vfolder, 'x', creator=admin)
    assert str(exc.value) == 'You cannot save a folder underneath a virtual folder.'


def testCannotMakeFolderWithChildrenVirtual(admin):
    folder = Folder().createFolder(admin, 'x', creator=admin, parentType='user')
    item = Item().createItem('x', creator=admin, folder=folder)
    folder['isVirtual'] = True

    with pytest.raises(ValidationException) as exc:
        Folder().save(folder)
    assert str(exc.value) == 'Virtual folders may not contain items.'

    subfolder = Folder().createFolder(folder, 'sub', creator=admin)
    Item().remove(item)

    with pytest.raises(ValidationException) as exc:
        Folder().save(folder)
    assert str(exc.value) == 'Virtual folders may not contain other folders.'

    Folder().remove(subfolder)

    assert Folder().save(folder)['isVirtual'] is True


def testVirtualFolderQuery(admin, vfolder, realFolder):
    Folder().setVirtualItemsQuery(vfolder, query={
        'meta.someVal': {
            '$gt': 5
        }
    }, sort=[('meta.someVal', SortDir.DESCENDING)])

    # Ensure we must explicitly pass virtualQuery to override default behavior
    assert list(Folder().childItems(vfolder)) == []
    assert list(Folder().childFolders(vfolder, user=admin)) == []

    items = Folder().childItems(vfolder, virtualQuery=True)
    assert [i['meta']['someVal'] for i in items] == [9, 8, 7, 6]

    # Keep default query, just change sort
    Folder().setVirtualFoldersQuery(vfolder, sort=[('name', SortDir.DESCENDING)])
    assert list(Folder().childFolders(vfolder, user=admin, virtualQuery=True)) == []

    # Now try with a custom query
    Folder().setVirtualFoldersQuery(vfolder, query={'description': 'foo'})
    folders = Folder().childFolders(vfolder, user=admin, virtualQuery=True)
    assert [f['name'] for f in folders] == [str(i) for i in reversed(range(10))]

    # Sort override at fetch time
    items = Folder().childItems(vfolder, sort=[('name', SortDir.ASCENDING)], virtualQuery=True)
    assert [i['name'] for i in items] == ['item6', 'item7', 'item8', 'item9']

    folders = Folder().childFolders(
        vfolder, sort=[('name', SortDir.ASCENDING)], user=admin, virtualQuery=True)
    assert [f['name'] for f in folders] == [str(i) for i in range(10)]

    # Deleting the virtual folder should not delete any of the real data
    Folder().remove(vfolder)
    assert Folder().load(vfolder['_id'], force=True) is None

    subfolders = list(Folder().childFolders(realFolder, user=admin))
    assert [f['name'] for f in subfolders] == [str(i) for i in range(10)]

    for f in subfolders:
        assert [i['name'] for i in Folder().childItems(f)] == ['item%s' % f['name']]


def testRestListingUsesVirtualQuery(admin, vfolder, realFolder, server):
    Folder().setVirtualFoldersQuery(vfolder, query={'description': 'foo'})
    Folder().setVirtualItemsQuery(vfolder, query={'meta.someVal': {'$gt': 5}})

    resp = server.request('/folder', user=admin, params={
        'parentType': 'folder',
        'parentId': vfolder['_id']
    })
    assert [f['name'] for f in resp.json] == [str(i) for i in range(10)]

    resp = server.request('/item', user=admin, params={
        'folderId': vfolder['_id']
    })
    assert [i['name'] for i in resp.json] == ['item6', 'item7', 'item8', 'item9']


def testSubtreeCountForVirtualFolder(vfolder, realFolder):
    Folder().setVirtualFoldersQuery(vfolder, query={'description': 'foo'})
    Folder().setVirtualItemsQuery(vfolder, query={'meta.someVal': {'$gt': 5}})

    assert Folder().subtreeCount(realFolder) == 21
    assert Folder().subtreeCount(vfolder) == 1
