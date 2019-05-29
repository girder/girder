# -*- coding: utf-8 -*-
from girder.plugin import GirderPlugin

from . import rest


class SentryPlugin(GirderPlugin):
    DISPLAY_NAME = 'Sentry'
    # CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].sentry = rest.Sentry()
