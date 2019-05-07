from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    DEFAULT_COLLECTION_QUOTA = 'user_quota.default_collection_quota'
    DEFAULT_USER_QUOTA = 'user_quota.default_user_quota'


@setting_utilities.default((
    PluginSettings.DEFAULT_COLLECTION_QUOTA,
    PluginSettings.DEFAULT_USER_QUOTA
))
def _defaultSettings():
    return None


@setting_utilities.validator((
    PluginSettings.DEFAULT_COLLECTION_QUOTA,
    PluginSettings.DEFAULT_USER_QUOTA
))
def _validateSettings(doc):
    from .quota import ValidateSizeQuota
    val = doc['value']

    val, err = ValidateSizeQuota(val)
    if err:
        raise ValidationException(err, 'value')
    doc['value'] = val
