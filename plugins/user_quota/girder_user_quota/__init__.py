# -*- coding: utf-8 -*-
from girder import events
from girder.exceptions import ValidationException
from girder.plugin import GirderPlugin
from girder.utility import setting_utilities

from . import constants
from .quota import QuotaPolicy, ValidateSizeQuota


@setting_utilities.validator((
    constants.PluginSettings.QUOTA_DEFAULT_USER_QUOTA,
    constants.PluginSettings.QUOTA_DEFAULT_COLLECTION_QUOTA
))
def validateSettings(doc):
    val = doc['value']

    val, err = ValidateSizeQuota(val)
    if err:
        raise ValidationException(err, 'value')
    doc['value'] = val


class UserQuotaPlugin(GirderPlugin):
    DISPLAY_NAME = 'User and collection quotas and policies'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        quota = QuotaPolicy()
        info['apiRoot'].collection.route('GET', (':id', 'quota'), quota.getCollectionQuota)
        info['apiRoot'].collection.route('PUT', (':id', 'quota'), quota.setCollectionQuota)
        info['apiRoot'].user.route('GET', (':id', 'quota'), quota.getUserQuota)
        info['apiRoot'].user.route('PUT', (':id', 'quota'), quota.setUserQuota)

        events.bind('model.upload.assetstore', 'userQuota', quota.getUploadAssetstore)
        events.bind('model.upload.save', 'userQuota', quota.checkUploadStart)
        events.bind('model.upload.finalize', 'userQuota', quota.checkUploadFinalize)
