#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################
import time

import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder.models.notification import Notification


def assertApproximateTimestamp(time1, time2, delta=1):
    __tracebackhide__ = True
    assert abs(float(time1) - float(time2)) < delta


@pytest.fixture
def notifications(user):
    model = Notification()
    doc1 = model.createNotification('type', {}, user)
    doc1['updated'] = 1
    doc1['time'] = 1
    model.save(doc1)
    doc2 = model.createNotification('type', {}, user)
    yield [doc1, doc2]
    model.remove(doc1)
    model.remove(doc2)


def testListAllNotifications(server, user, notifications):
    resp = server.request(path='/notification', user=user)
    assertStatusOk(resp)
    assert {m['_id'] for m in resp.json} == {str(m['_id']) for m in notifications}
    assertApproximateTimestamp(resp.headers.get('Date'), notifications[1]['updatedTime'])


def testListNotificationsSinceTime(server, user, notifications):
    resp = server.request(path='/notification', user=user, params={'since': 10})
    assertStatusOk(resp)
    assert {m['_id'] for m in resp.json} == {str(notifications[-1]['_id'])}
    assertApproximateTimestamp(resp.headers.get('Date'), notifications[1]['updatedTime'])


def testDefaultDateHeader(server, user, notifications):
    resp = server.request(path='/notification', user=user,
                          params={'since': int(time.time()) + 1000})
    assertStatusOk(resp)
    assert resp.json == []
    assertApproximateTimestamp(resp.headers.get('Date'), time.time(), 10)


def testListNotificationsAuthError(server, notifications):
    resp = server.request(path='/notification')
    assertStatus(resp, 401)
