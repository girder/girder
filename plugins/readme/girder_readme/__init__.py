# -*- coding: utf-8 -*-
from girder.plugin import GirderPlugin
from .rest import _getFolderReadme


class ReadmePlugin(GirderPlugin):
    DISPLAY_NAME = 'README'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].folder.route('GET', (':id', 'readme'), _getFolderReadme)
