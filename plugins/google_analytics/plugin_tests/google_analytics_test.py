# -*- coding: utf-8 -*-
from tests import base
from girder.models.setting import Setting

from girder_google_analytics.settings import PluginSettings


def setUpModule():
    base.enabledPlugins.append('google_analytics')
    base.startServer()


def tearDownModule():
    base.stopServer()


class GoogleAnalyticsTest(base.TestCase):

    def testGetAnalytics(self):
        # test without set
        resp = self.request('/google_analytics/id')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['google_analytics_id'], '')

        # set tracking id
        Setting().set(PluginSettings.TRACKING_ID, 'testing-tracking-id')

        # verify we can get the tracking id without being authenticated.
        resp = self.request('/google_analytics/id')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['google_analytics_id'], 'testing-tracking-id')
