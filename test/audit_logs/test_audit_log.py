import datetime
import pytest
import six
from girder import auditLogger
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload


@pytest.fixture
def recordModel():
    from girder.plugins.audit_logs import Record
    yield Record()


@pytest.fixture
def freshLog():
    yield auditLogger

    for handler in auditLogger.handlers:
        auditLogger.removeHandler(handler)


@pytest.mark.plugin('audit_logs')
def testAnonymousRestRequestLogging(server, recordModel, freshLog):
    assert list(recordModel.find()) == []

    server.request('/user/me')

    records = recordModel.find()
    assert records.count() == 1
    record = records[0]

    assert record['ip'] == '127.0.0.1'
    assert record['type'] == 'rest.request'
    assert record['userId'] == None
    assert isinstance(record['when'], datetime.datetime)
    assert record['details']['method'] == 'GET'
    assert record['details']['status'] == 200
    assert record['details']['route'] == ['user', 'me']
    assert record['details']['params'] == {}


@pytest.mark.plugin('audit_logs')
def testFailedRestRequestLogging(server, recordModel, freshLog):
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
    server.request('/user/me', user=admin)
    records = recordModel.find()
    assert records.count() == 1
    record = records[0]
    assert record['userId'] == admin['_id']


@pytest.mark.plugin('audit_logs')
def testDownloadLogging(server, recordModel, freshLog, admin, fsAssetstore):
    folder = Folder().find({
        'parentId': admin['_id'],
        'name': 'Public'
    })[0]
    file = Upload().uploadFromFile(
        six.BytesIO(b'hello'), size=5, name='test', parentType='folder', parent=folder,
        user=admin, assetstore=fsAssetstore)

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
