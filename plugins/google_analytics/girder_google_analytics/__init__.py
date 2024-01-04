from pathlib import Path

from girder.plugin import GirderPlugin, registerPluginStaticContent

from . import rest


class GoogleAnalyticsPlugin(GirderPlugin):
    DISPLAY_NAME = 'Google Analytics'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].google_analytics = rest.GoogleAnalytics()

        registerPluginStaticContent(
            plugin='google_analytics',
            css=['/style.css'],
            js=['/girder-plugin-google-analytics.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
        )
