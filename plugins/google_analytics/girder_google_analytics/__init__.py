# -*- coding: utf-8 -*-
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
