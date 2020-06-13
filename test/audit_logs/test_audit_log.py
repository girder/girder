import datetime
import io
import pytest
from click.testing import CliRunner
from girder import auditLogger
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.upload import Upload
from girder.models.user import User
from girder_audit_logs import Record, cleanup


@pytest.fixture
def freshLog():
    Record().collection.drop()  # Clear existing records

    yield auditLogger

    for handler in auditLogger.handlers:
        auditLogger.removeHandler(handler)


@pytest.mark.plugin('audit_logs')
def testAnonymousRestRequestLogging(server, freshLog):
    Record().collection.delete_many({})  # Clear existing records
    server.request('/user/me')

    records = Record().find()
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
def testFailedRestRequestLogging(server, freshLog):
    server.request('/folder', method='POST', params={
        'name': 'Foo',
        'parentId': 'foo'
    })
    records = Record().find()

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
def testAuthenticatedRestRequestLogging(server, admin, freshLog):
    server.request('/user/me', user=admin)
    records = Record().find()
    assert records.count() == 1
    record = records[0]
    assert record['userId'] == admin['_id']


@pytest.mark.parametrize('requestParams, logParams', [
    ({'foo': 'bar'}, {'foo': 'bar'}),
    ({'foo\x00': 'bar'}, {'foo%00': 'bar'}),
    ({'\x00': 'bar'}, {'%00': 'bar'}),
    ({'fo.o': 'bar'}, {'fo%2Eo': 'bar'}),
    ({'fo$o': 'bar'}, {'fo%24o': 'bar'}),
])
@pytest.mark.plugin('audit_logs')
def testDangerousParamsRestRequestLogging(server, admin, freshLog, requestParams, logParams):
    server.request('/folder', params=requestParams)

    records = Record().find()
    assert records.count() == 1
    details = records[0]['details']
    assert details['params'] == logParams


@pytest.mark.plugin('audit_logs')
def testDownloadLogging(server, admin, fsAssetstore, freshLog):
    folder = Folder().find({
        'parentId': admin['_id'],
        'name': 'Public'
    })[0]
    file = Upload().uploadFromFile(
        io.BytesIO(b'hello'), size=5, name='test', parentType='folder', parent=folder,
        user=admin, assetstore=fsAssetstore)

    Record().collection.delete_many({})  # Clear existing records

    File().download(file, headers=False, offset=2, endByte=4)

    records = Record().find()

    assert records.count() == 1
    record = records[0]
    assert record['ip'] == '127.0.0.1'
    assert record['type'] == 'file.download'
    assert record['details']['fileId'] == file['_id']
    assert record['details']['startByte'] == 2
    assert record['details']['endByte'] == 4
    assert isinstance(record['when'], datetime.datetime)


@pytest.mark.plugin('audit_logs')
def testDocumentCreationLogging(server, freshLog):
    user = User().createUser('admin', 'password', 'first', 'last', 'a@a.com')
    records = Record().find(sort=[('when', 1)])
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
def testCleanupScript(server, freshLog, args, expected, admin):
    server.request('/user/me', user=admin)

    result = CliRunner().invoke(cleanup.cleanup, args)
    assert result.exit_code == 0
    assert result.output == 'Deleted %d log entries.\n' % expected


@pytest.mark.plugin('audit_logs')
def testDisableLoggingOnNotificationEndpoints(server, user, freshLog):
    server.request('/user/me')
    server.request('/notification', user=user)
    server.request('/notification/stream', params={'timeout': 0}, user=user, isJson=False)
    assert Record().find().count() == 1
