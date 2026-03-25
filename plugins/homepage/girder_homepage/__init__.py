from pathlib import Path

from girder.plugin import GirderPlugin, registerPluginStaticContent

from . import rest


class HomepagePlugin(GirderPlugin):
    DISPLAY_NAME = 'Homepage'

    def load(self, info):
        info['apiRoot'].homepage = rest.Homepage()

        registerPluginStaticContent(
            plugin='homepage',
            css=['/style.css'],
            js=['/girder-plugin-homepage.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
