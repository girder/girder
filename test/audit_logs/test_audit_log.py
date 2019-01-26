import datetime
import pytest
import six
from girder import auditLogger
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.models.user import User
from girder_audit_logs import Record


@pytest.fixture
def recordModel():
    yield Record()


@pytest.fixture
def freshLog():
    yield auditLogger

    for handler in auditLogger.handlers:
        auditLogger.removeHandler(handler)


@pytest.mark.plugin('audit_logs')
def testAnonymousRestRequestLogging(server, recordModel, freshLog):
    recordModel.collection.delete_many({})  # Clear existing records
    server.request('/user/me')

    records = recordModel.find()
    assert records.count() == 1
    record = records[0]

    assert record['ip'] == '127.0.0.1'
    assert record['type'] == 'rest.request'
    assert record['userId'] is None
    assert isinstance(record['when'], datetime.datetime)
    assert record['details']['method'] == 'GET'
    assert record['details']['status'] == 200
    assert record['details']['route'] == ['user', 'me']
    assert record['details']['params'] == {}


@pytest.mark.plugin('audit_logs')
def testFailedRestRequestLogging(server, recordModel, freshLog):
    recordModel.collection.delete_many({})  # Clear existing records
    server.request('/folder', method='POST', params={
        'name': 'Foo',
        'parentId': 'foo'
    })
    records = recordModel.find()

    assert records.count() == 1
    details = records[0]['details']

    assert details['method'] == 'POST'
    assert details['status'] == 401
    assert details['route'] == ['folder']
    assert details['params'] == {
        'name': 'Foo',
        'parentId': 'foo'
    }


@pytest.mark.plugin('audit_logs')
def testAuthenticatedRestRequestLogging(server, recordModel, freshLog, admin):
    recordModel.collection.delete_many({})  # Clear existing records
    server.request('/user/me', user=admin)
    records = recordModel.find()
    assert records.count() == 1
    record = records[0]
    assert record['userId'] == admin['_id']


@pytest.mark.plugin('audit_logs')
def testDownloadLogging(server, recordModel, freshLog, admin, fsAssetstore):
    recordModel.collection.delete_many({})  # Clear existing records
    folder = Folder().find({
        'parentId': admin['_id'],
        'name': 'Public'
    })[0]
    file = Upload().uploadFromFile(
        six.BytesIO(b'hello'), size=5, name='test', parentType='folder', parent=folder,
        user=admin, assetstore=fsAssetstore)

    recordModel.collection.delete_many({})  # Clear existing records

    File().download(file, headers=False, offset=2, endByte=4)

    records = recordModel.find()

    assert records.count() == 1
    record = records[0]
    assert record['ip'] == '127.0.0.1'
    assert record['type'] == 'file.download'
    assert record['details']['fileId'] == file['_id']
    assert record['details']['startByte'] == 2
    assert record['details']['endByte'] == 4
    assert isinstance(record['when'], datetime.datetime)


@pytest.mark.plugin('audit_logs')
def testDocumentCreationLogging(server, recordModel, freshLog):
    recordModel.collection.delete_many({})  # Clear existing records
    user = User().createUser('admin', 'password', 'first', 'last', 'a@a.com')
    records = recordModel.find(sort=[('when', 1)])
    assert records.count() == 3

    assert records[0]['details']['collection'] == 'user'
    assert records[0]['details']['id'] == user['_id']
    assert records[1]['details']['collection'] == 'folder'
    assert records[2]['details']['collection'] == 'folder'
