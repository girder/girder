import pytest
import six

from girder.models.upload import Upload


@pytest.fixture
def folder(user):
    from girder.models.folder import Folder
    folder = Folder().createFolder(user, 'some-folder')

    yield folder

    Folder().remove(folder)


@pytest.fixture
def item(folder, user):
    from girder.models.item import Item
    item = Item().createItem('some-item', user, folder)

    yield item

    Item().remove(item)


@pytest.fixture
def filesystemAssetstore(db, tmpdir):
    from girder.models.assetstore import Assetstore
    assetstore = Assetstore().createFilesystemAssetstore(name='test-assetstore',
                                                         root=tmpdir.strpath)

    yield assetstore

    Assetstore().remove(assetstore)


def testMultipartUploadOfUnknownSize(db, filesystemAssetstore, item, user):
    fileBytes = six.BytesIO(b'abcdefgh')
    upload = Upload().createUpload(user=user, name=item['name'], parentType='item',
                                   parent=item, assetstore=filesystemAssetstore)

    for chunk in fileBytes:
        Upload().handleChunk(upload, chunk)

    createdFile = Upload().finalizeUpload(upload, filesystemAssetstore)
    assert createdFile['size'] == 8
