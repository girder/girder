# -*- coding: utf-8 -*-
import time

from .. import base

from girder.exceptions import ValidationException
from girder.models.notification import ProgressState
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User
from girder.settings import SettingKey
from girder.utility.progress import ProgressContext


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class NotificationTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        self.admin = User().createUser(
            email='admin@girder.test', login='admin', firstName='first',
            lastName='last', password='mypasswd')

    def _testStream(self, user, token=None):
        # Should only work for users or token sessions
        resp = self.request(path='/notification/stream', method='GET')
        self.assertStatus(resp, 401)
        self.assertEqual(
            resp.json['message'],
            'You must be logged in or have a valid auth token.')

        resp = self.request(path='/notification/stream', method='GET',
                            user=user, token=token, isJson=False,
                            params={'timeout': 0})
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), '')

        # Should not work when disabled
        Setting().set(SettingKey.ENABLE_NOTIFICATION_STREAM, False)
        resp = self.request(path='/notification/stream', method='GET',
                            user=user, token=token, isJson=False,
                            params={'timeout': 0})
        self.assertStatus(resp, 503)
        Setting().set(SettingKey.ENABLE_NOTIFICATION_STREAM, True)

        # Use a very high rate-limit interval so that we don't fail on slow
        # build boxes
        with ProgressContext(
                True, user=user, token=token, title='Test', total=100,
                interval=100) as progress:
            progress.update(current=1)

            # Rate limiting should make it so we didn't write the immediate
            # update within the time interval.
            resp = self.request(path='/notification/stream', method='GET',
                                user=user, token=token, isJson=False,
                                params={'timeout': 0})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['type'], 'progress')
            self.assertEqual(messages[0]['data']['total'], 100)
            self.assertEqual(messages[0]['data']['current'], 0)
            self.assertFalse(ProgressState.isComplete(
                messages[0]['data']['state']))

            # Now use a very short interval to test that we do save changes
            progress.interval = 0.01
            time.sleep(0.02)
            progress.update(current=2)
            resp = self.request(path='/notification/stream', method='GET',
                                user=user, token=token, isJson=False,
                                params={'timeout': 0})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['data']['current'], 2)
            # If we use a non-numeric value, nothing bad should happen
            time.sleep(0.02)
            progress.update(current='not_a_number')
            resp = self.request(path='/notification/stream', method='GET',
                                user=user, token=token, isJson=False,
                                params={'timeout': 0})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['data']['current'], 'not_a_number')
            # Updating the progress without saving and then exiting should
            # send the update.
            progress.interval = 1000
            progress.update(current=3)

            # The message should contain a timestamp
            self.assertIn('_girderTime', messages[0])
            self.assertIsInstance(messages[0]['_girderTime'], int)

            # Test that the "since" parameter correctly filters out messages
            since = messages[0]['_girderTime'] + 1
            resp = self.request(path='/notification/stream', method='GET',
                                user=user, token=token, isJson=False,
                                params={'timeout': 0, 'since': since})
            messages = self.getSseMessages(resp)
            self.assertEqual(len(messages), 0)

        # Exiting the context manager should flush the most recent update.
        resp = self.request(path='/notification/stream', method='GET',
                            user=user, token=token, isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['data']['current'], 3)

        # Test a ValidationException within the progress context
        try:
            with ProgressContext(True, user=user, token=token, title='Test', total=100):
                raise ValidationException('Test Message')
        except ValidationException:
            pass

        # Exiting the context manager should flush the most recent update.
        resp = self.request(path='/notification/stream', method='GET',
                            user=user, token=token, isJson=False,
                            params={'timeout': 0})
        messages = self.getSseMessages(resp)
        self.assertEqual(messages[-1]['data']['message'],
                         'Error: Test Message')

    def testUserStream(self):
        self._testStream(self.admin)

    def testTokenStream(self):
        resp = self.request(path='/token/session', method='GET')
        self.assertStatusOk(resp)
        token = resp.json['token']
        tokenDoc = Token().load(token, force=True, objectId=False)
        self._testStream(None, tokenDoc)
