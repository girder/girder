from girder.models.model_base import ValidationException
from girder.utility import setting_utilities

from .constants import PluginSettings


@setting_utilities.default(PluginSettings.ITEM_METADATA)
def defaultItemMetadata():
    return 'default_value'


@setting_utilities.validator(PluginSettings.ITEM_METADATA)
def validateItemMetadata(settingDoc):
    settingValue = settingDoc['value']

    if not len(settingValue):
        raise ValidationException('Item metadata is required.', 'value')
