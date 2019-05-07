# -*- coding: utf-8 -*-
from girder.plugin import GirderPlugin

from . import rest


class GoogleAnalyticsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Google Analytics'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].google_analytics = rest.GoogleAnalytics()
