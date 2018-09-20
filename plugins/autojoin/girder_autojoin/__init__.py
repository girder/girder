import jsonschema

from girder import events
from girder.exceptions import ValidationException
from girder.utility import setting_utilities
from girder.models.group import Group
from girder.models.setting import Setting
from girder.plugin import GirderPlugin

_autojoinSchema = {
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


@setting_utilities.validator('autojoin')
def validateSettings(doc):
    try:
        jsonschema.validate(doc['value'], _autojoinSchema)
    except jsonschema.ValidationError as e:
        raise ValidationException('Invalid autojoin rules: ' + e.message)


def userCreated(event):
    """
    Check auto join rules when a new user is created. If a match is found,
    add the user to the group with the specified access level.
    """
    user = event.info
    email = user.get('email').lower()
    rules = Setting().get('autojoin', [])
    for rule in rules:
        if rule['pattern'].lower() not in email:
            continue
        group = Group().load(rule['groupId'], force=True)
        if group:
            Group().addUser(group, user, rule['level'])


class AutojoinPlugin(GirderPlugin):
    DISPLAY_NAME = 'Auto Join'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        events.bind('model.user.save.created', 'autojoin', userCreated)
