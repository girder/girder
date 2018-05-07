import datetime
import pytest
from girder import auditLogger


@pytest.fixture
def recordModel():
    from girder.plugins.audit_logs import Record
    yield Record()


@pytest.fixture
def resetLog():
    yield auditLogger

    for handler in auditLogger.handlers:
        auditLogger.removeHandler(handler)


@pytest.mark.plugin('audit_logs')
def testAnonymousRestRequestLogging(server, recordModel, resetLog):
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
def testFailedRestRequestLogging(server, recordModel, resetLog):
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
def testAuthenticatedRestRequestLogging(server, recordModel, resetLog, admin):
    server.request('/user/me', user=admin)
    records = recordModel.find()
    assert records.count() == 1
    record = records[0]
    assert record['userId'] == admin['_id']
