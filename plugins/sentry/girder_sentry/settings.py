from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings:
    FRONTEND_DSN = 'sentry.frontend_dsn'
    BACKEND_DSN = 'sentry.backend_dsn'


@setting_utilities.default(PluginSettings.FRONTEND_DSN)
@setting_utilities.default(PluginSettings.BACKEND_DSN)
def _defaultDsn():
    return ''


@setting_utilities.validator(PluginSettings.FRONTEND_DSN)
@setting_utilities.validator(PluginSettings.BACKEND_DSN)
def _validateDsn(doc):
    if not doc['value']:
        raise ValidationException('DSN must not be empty.', 'value')
