from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    TRACKING_ID = 'google_analytics.tracking_id'


@setting_utilities.default(PluginSettings.TRACKING_ID)
def _defaultTrackingId():
    return ''


@setting_utilities.validator(PluginSettings.TRACKING_ID)
def _validateTrackingId(doc):
    if not doc['value']:
        raise ValidationException('Google Analytics Tracking ID must not be empty.', 'value')
