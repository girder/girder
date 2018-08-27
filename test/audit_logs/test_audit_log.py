import datetime
import pytest
import six
from click.testing import CliRunner
from girder import auditLogger
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.models.user import User


@pytest.fixture
def recordModel():
    from girder.plugins.audit_logs import Record
    yield Record()


@pytest.fixture
def cleanupCli():
    from girder.plugins.audit_logs import cleanup
    yield cleanup.cleanup


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
    recordModel.collection.drop()  # Clear existing records
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

    recordModel.collection.remove({})  # Clear existing records

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
    user = User().createUser('admin', 'password', 'first', 'last', 'a@a.com')
    records = recordModel.find(sort=[('when', 1)])
    assert records.count() == 3

    assert records[0]['details']['collection'] == 'user'
    assert records[0]['details']['id'] == user['_id']
    assert records[1]['details']['collection'] == 'folder'
    assert records[2]['details']['collection'] == 'folder'


@pytest.mark.plugin('audit_logs')
@pytest.mark.parametrize('args,expected', [
    ([], 0),
    (['--days=0'], 4),
    (['--days=0', '--types=rest.request'], 1),
    (['--days=0', '--types=document.create'], 3)
])
def testCleanupScript(server, freshLog, recordModel, cleanupCli, args, expected):
    user = User().createUser('admin', 'password', 'first', 'last', 'a@a.com')
    server.request('/user/me', user=user)

    result = CliRunner().invoke(cleanupCli, args)
    assert result.exit_code == 0
    assert result.output == 'Deleted %d log entries.\n' % expected


@pytest.mark.plugin('audit_logs')
def testDisableLoggingOnNotificationEndpoints(server, freshLog, recordModel, user):
    recordModel.collection.drop()
    server.request('/user/me')
    server.request('/notification', user=user)
    server.request('/notification/stream', params={'timeout': 0}, user=user, isJson=False)
    assert recordModel.find().count() == 1
