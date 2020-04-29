# -*- coding: utf-8 -*-
from girder.plugin import GirderPlugin
from . import rest


class ReadmePlugin(GirderPlugin):
    DISPLAY_NAME = 'README'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].folder = rest.FolderReadme()
