# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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
