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

from girder.exceptions import ValidationException
from girder.plugin import GirderPlugin
from girder.utility import setting_utilities

from . import constants, rest


@setting_utilities.validator(constants.PluginSettings.GOOGLE_ANALYTICS_TRACKING_ID)
def validateTrackingId(doc):
    if not doc['value']:
        raise ValidationException('Google Analytics Tracking ID must not be empty.', 'value')


class GoogleAnalyticsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Google Analytics'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].google_analytics = rest.GoogleAnalytics()
