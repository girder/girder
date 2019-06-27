from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    _FRONTEND_DSN = 'sentry.frontend_dsn'
    _BACKEND_DSN = 'sentry.backend_dsn'


@setting_utilities.default(PluginSettings._FRONTEND_DSN)
@setting_utilities.default(PluginSettings._BACKEND_DSN)
def _defaultDsn():
    return ''


@setting_utilities.validator(PluginSettings._FRONTEND_DSN)
@setting_utilities.validator(PluginSettings._BACKEND_DSN)
def _validateDsn(doc):
    if not doc['value']:
        raise ValidationException('DSN must not be empty.', 'value')
