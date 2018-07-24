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
import pytest
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder.models.notification import Notification


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


def testListNotificationsSinceTime(server, user, notifications):
    resp = server.request(path='/notification', user=user, params={'since': 10})
    assertStatusOk(resp)
    assert {m['_id'] for m in resp.json} == {str(notifications[-1]['_id'])}


def testListNotificationsAuthError(server, notifications):
    resp = server.request(path='/notification')
    assertStatus(resp, 401)
