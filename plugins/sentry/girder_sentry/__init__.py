from pathlib import Path

import sentry_sdk
from girder.plugin import GirderPlugin, registerPluginStaticContent
from girder.models.setting import Setting

from . import rest
from .settings import PluginSettings


class SentryPlugin(GirderPlugin):
    DISPLAY_NAME = 'Sentry'

    def load(self, info):
        info['apiRoot'].sentry = rest.Sentry()

        sentry_sdk.init(dsn=Setting().get(PluginSettings.BACKEND_DSN))

        registerPluginStaticContent(
            plugin='sentry',
            css=['/style.css'],
            js=['/girder-plugin-sentry.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
