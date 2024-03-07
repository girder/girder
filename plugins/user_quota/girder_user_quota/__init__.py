from pathlib import Path

from girder import events
from girder.plugin import GirderPlugin, registerPluginStaticContent

from .quota import QuotaPolicy


class UserQuotaPlugin(GirderPlugin):
    DISPLAY_NAME = 'User and Collection Quotas'

    def load(self, info):
        quota = QuotaPolicy()
        info['apiRoot'].collection.route('GET', (':id', 'quota'), quota.getCollectionQuota)
        info['apiRoot'].collection.route('PUT', (':id', 'quota'), quota.setCollectionQuota)
        info['apiRoot'].user.route('GET', (':id', 'quota'), quota.getUserQuota)
        info['apiRoot'].user.route('PUT', (':id', 'quota'), quota.setUserQuota)

        events.bind('model.upload.assetstore', 'userQuota', quota.getUploadAssetstore)
        events.bind('model.upload.save', 'userQuota', quota.checkUploadStart)
        events.bind('model.upload.finalize', 'userQuota', quota.checkUploadFinalize)

        registerPluginStaticContent(
            plugin='user_quota',
            css=['/style.css'],
            js=['/girder-plugin-user-quota.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
