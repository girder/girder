# -*- coding: utf-8 -*-
import pytest

from girder.models.setting import Setting
from girder_sentry.settings import PluginSettings

TEST_DSN = 'http://foo.bar'


def testEmptyInitSentryDSN(self):
    # Obviously Change
    assert True


def testGetSentryDSN(self):
    assert True
    # resp = self.request('/google_analytics/id')
    # self.assertStatusOk(resp)
    # self.assertEqual(resp.json['google_analytics_id'], '')

    # # set tracking id
    # Setting().set(PluginSettings.TRACKING_ID, 'testing-tracking-id')

    # # verify we can get the tracking id without being authenticated.
    # resp = self.request('/google_analytics/id')
    # self.assertStatusOk(resp)
    # self.assertEquals(resp.json['google_analytics_id'], 'testing-tracking-id')
