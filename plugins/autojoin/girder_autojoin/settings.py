import jsonschema

from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings:
    AUTOJOIN = 'autojoin'


@setting_utilities.default(PluginSettings.AUTOJOIN)
def _defaultAutojoin():
    return []


@setting_utilities.validator(PluginSettings.AUTOJOIN)
def _validateAutojoin(doc):
    autojoinSchema = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string'
                },
                'groupId': {
                    'type': 'string',
                    'minLength': 1
                },
                'level': {
                    'type': 'number'
                }
            },
            'required': ['pattern', 'groupId', 'level']
        }
    }
    try:
        jsonschema.validate(doc['value'], autojoinSchema)
    except jsonschema.ValidationError as e:
        raise ValidationException('Invalid autojoin rules: ' + str(e))
