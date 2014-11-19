#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import json
import time

from .. import base

from girder.models.model_base import ValidationException
from girder.utility.progress import ProgressContext


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class NotificationTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.admin = self.model('user').createUser(
            email='admin@email.com', login='admin', firstName='first',
            lastName='last', password='mypasswd')

    def getSseMessages(self, resp):
        messages = resp.collapse_body().strip().split('\n\n')
        return map(lambda m: json.loads(m.replace('data: ', '')), messages)

    def testStream(self):
        # Should only work for users
        resp = self.request(path='/notification/stream', method='GET')
        self.assertStatus(resp, 401)
        self.assertEqual(resp.json['message'], 'You must be logged in.')

        resp = self.request(path='/notification/stream', method='GET',
                            user=self.admin, isJson=False,
                            params={'timeout': 1})
        self.assertStatusOk(resp)
        self.assertEqual(resp.collapse_body(), '')

        # Use a very high rate-limit interval so that we don't fail on slow
        # build boxes
        with ProgressContext(
                True, user=self.admin, title='Test', total=100,
                interval=100) as progress:
            progress.update(current=1)

            # Rate limiting should make it so we didn't write the immediate
            # update within the time interval.
            resp = self.request(path='/notification/stream', method='GET',
                                user=self.admin, isJson=False,
                                params={'timeout': 1})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['type'], 'progress')
            self.assertEqual(messages[0]['data']['total'], 100)
            self.assertEqual(messages[0]['data']['current'], 0)

            # Now use a very short interval to test that we do save changes
            progress.interval = 0.01
            time.sleep(0.02)
            progress.update(current=2)
            resp = self.request(path='/notification/stream', method='GET',
                                user=self.admin, isJson=False,
                                params={'timeout': 1})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['data']['current'], 2)

        # Exiting the context manager should flush the most recent update.
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.admin, isJson=False,
                            params={'timeout': 1})
        messages = self.getSseMessages(resp)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['data']['current'], 2)

        # Test a ValidationException within the progress context
        try:
            with ProgressContext(
                    True, user=self.admin, title='Test',
                    total=100) as progress:
                raise ValidationException('Test Message')
        except ValidationException:
            pass

        # Exiting the context manager should flush the most recent update.
        resp = self.request(path='/notification/stream', method='GET',
                            user=self.admin, isJson=False,
                            params={'timeout': 1})
        messages = self.getSseMessages(resp)
        self.assertEqual(messages[-1]['data']['message'],
                         'Error: Test Message')
