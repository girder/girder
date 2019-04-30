# -*- coding: utf-8 -*-
import datetime
import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk
from girder.models.notification import Notification

OLD_TIME = datetime.datetime.utcnow() - datetime.timedelta(days=3)
SINCE = OLD_TIME + datetime.timedelta(days=1)


@pytest.fixture
def notifications(user):
    model = Notification()
    doc1 = model.createNotification('type', {}, user)
    doc2 = model.createNotification('type', {}, user)
    doc2['updated'] = OLD_TIME
    doc2['time'] = OLD_TIME
    model.save(doc2)

    yield [doc1, doc2]


def testListAllNotifications(server, user, notifications):
    resp = server.request(path='/notification', user=user)
    assertStatusOk(resp)
    n1, n2 = notifications
    # Make sure we get results back in chronological order
    assert [n['_id'] for n in resp.json] == [str(n2['_id']), str(n1['_id'])]


def testListNotificationsSinceTime(server, user, notifications):
    resp = server.request(path='/notification', user=user, params={'since': SINCE.isoformat()})
    assertStatusOk(resp)
    assert len(resp.json) == 1
    assert resp.json[0]['_id'] == str(notifications[0]['_id'])


def testListNotificationsAuthError(server):
    resp = server.request(path='/notification')
    assertStatus(resp, 401)
