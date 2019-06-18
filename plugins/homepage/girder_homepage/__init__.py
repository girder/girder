# -*- coding: utf-8 -*-
from girder.plugin import GirderPlugin

from . import rest


class HomepagePlugin(GirderPlugin):
    DISPLAY_NAME = 'Homepage'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].homepage = rest.Homepage()
