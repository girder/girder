from bson.objectid import ObjectId

from girder.constants import AssetstoreType
from girder.exceptions import ValidationException
from girder.models.assetstore import Assetstore
from girder.utility import setting_utilities


class PluginSettings:
    # The ID of the filesystem assetstore that local copies are placed in.  If
    # empty, the current default assetstore is used when it is a filesystem
    # assetstore.
    ASSETSTORE_ID = 'local_checkout.assetstore_id'
    # The longest checkout duration, in days, that may be requested.
    MAX_DAYS = 'local_checkout.max_days'
    # If true, only site administrators may check out folders.
    ADMIN_ONLY = 'local_checkout.admin_only'


@setting_utilities.default(PluginSettings.ASSETSTORE_ID)
def _defaultAssetstoreId():
    return ''


@setting_utilities.default(PluginSettings.MAX_DAYS)
def _defaultMaxDays():
    return 90


@setting_utilities.default(PluginSettings.ADMIN_ONLY)
def _defaultAdminOnly():
    return False


@setting_utilities.validator(PluginSettings.ASSETSTORE_ID)
def _validateAssetstoreId(doc):
    value = doc['value']
    if value in (None, ''):
        doc['value'] = ''
        return
    try:
        assetstore = Assetstore().load(ObjectId(str(value)))
    except Exception:
        assetstore = None
    if assetstore is None:
        raise ValidationException('Assetstore ID must refer to an existing assetstore.', 'value')
    if assetstore['type'] != AssetstoreType.FILESYSTEM:
        raise ValidationException('The checkout assetstore must be a filesystem assetstore.',
                                  'value')
    doc['value'] = str(assetstore['_id'])


@setting_utilities.validator(PluginSettings.MAX_DAYS)
def _validateMaxDays(doc):
    try:
        value = int(doc['value'])
    except (TypeError, ValueError):
        raise ValidationException('Maximum checkout days must be an integer.', 'value')
    if value < 1:
        raise ValidationException('Maximum checkout days must be at least 1.', 'value')
    doc['value'] = value


@setting_utilities.validator(PluginSettings.ADMIN_ONLY)
def _validateAdminOnly(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('Admin-only setting must be true or false.', 'value')
