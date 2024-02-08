from pathlib import Path

from girder.plugin import GirderPlugin, registerPluginStaticContent
from .rest import _getFolderReadme


class ReadmePlugin(GirderPlugin):
    DISPLAY_NAME = 'README'

    def load(self, info):
        info['apiRoot'].folder.route('GET', (':id', 'readme'), _getFolderReadme)

        registerPluginStaticContent(
            plugin='readme',
            css=['/style.css'],
            js=['/girder-plugin-readme.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
