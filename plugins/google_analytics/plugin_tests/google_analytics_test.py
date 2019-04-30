# -*- coding: utf-8 -*-
from tests import base
from girder.models.setting import Setting

from girder_google_analytics.constants import PluginSettings


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
        self.assertIs(resp.json['google_analytics_id'], None)

        # set tracking id
        Setting().set(PluginSettings.GOOGLE_ANALYTICS_TRACKING_ID, 'testing-tracking-id')

        # verify we can get the tracking id without being authenticated.
        resp = self.request('/google_analytics/id')
        self.assertStatusOk(resp)
        self.assertEquals(resp.json['google_analytics_id'], 'testing-tracking-id')
