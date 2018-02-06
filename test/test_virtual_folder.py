import pytest

from girder.constants import SortDir
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.item import Item


@pytest.fixture
def vfolder(admin):
    folder = Folder().createFolder(admin, 'virtual', parentType='user', virtual=True)
    yield folder
    Folder().remove(folder)


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


def testVirtualFolderQuery(admin, vfolder):
    realParent = Folder().createFolder(admin, 'x', creator=admin, parentType='user')

    for i in range(10):
        subfolder = Folder().createFolder(realParent, str(i), creator=admin, description='foo')
        item = Item().createItem('item' + str(i), creator=admin, folder=subfolder)
        Item().setMetadata(item, {
            'someVal': i
        })

    Folder().setVirtualItemsQuery(vfolder, query={
        'meta.someVal': {
            '$gt': 5
        }
    }, sort=[('meta.someVal', SortDir.DESCENDING)])
    items = Folder().childItems(vfolder)
    assert [i['meta']['someVal'] for i in items] == [9, 8, 7, 6]

    # Keep default query, just change sort
    Folder().setVirtualFoldersQuery(vfolder, sort=[('name', SortDir.DESCENDING)])
    assert list(Folder().childFolders(vfolder, user=admin)) == []

    # Now try with a custom query
    Folder().setVirtualFoldersQuery(vfolder, query={'description': 'foo'})
    folders = Folder().childFolders(vfolder, user=admin)
    assert [f['name'] for f in folders] == [str(i) for i in reversed(range(10))]

    # Sort override at fetch time
    items = Folder().childItems(vfolder, sort=[('name', SortDir.ASCENDING)])
    assert [i['name'] for i in items] == ['item6', 'item7', 'item8', 'item9']

    folders = Folder().childFolders(vfolder, sort=[('name', SortDir.ASCENDING)], user=admin)
    assert [f['name'] for f in folders] == [str(i) for i in range(10)]
