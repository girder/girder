from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    DSN = 'sentry.dsn'


@setting_utilities.default(PluginSettings.DSN)
def _defaultDsn():
    return ''


@setting_utilities.validator(PluginSettings.DSN)
def _validateDsn(doc):
    if not doc['value']:
        raise ValidationException('Sentry DSN must not be empty.', 'value')
