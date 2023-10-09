import jsonschema

from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings:
    SERVERS = 'ldap.servers'
    SETTINGS = 'ldap.settings'


@setting_utilities.default(PluginSettings.SETTINGS)
def _defaultSettings():
    return {
        'timeout': 4,
        'fallback': True,
    }


@setting_utilities.validator(PluginSettings.SETTINGS)
def _validateSettings(doc):
    settingSchema = {
        'type': 'object',
        'properties': {
            'timeout': {
                'type': 'number',
            },
            'fallback': {
                'type': 'boolean',
            },
        },
        'required': ['fallback', 'timeout'],
    }
    try:
        jsonschema.validate(doc['value'], settingSchema)
    except jsonschema.ValidationError as e:
        raise ValidationException('Invalid Settings Schema' + str(e))

    settings = doc['value']
    settings['timeout'] = settings.get('timeout', 4)
    settings['fallback'] = settings.get('fallback', True)


@setting_utilities.default(PluginSettings.SERVERS)
def _defaultServers():
    return []


@setting_utilities.validator(PluginSettings.SERVERS)
def _validateServers(doc):
    serversSchema = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'uri': {'type': 'string', 'minLength': 1},
                'bindName': {'type': 'string', 'minLength': 1},
                'baseDn': {'type': 'string'},
            },
            'required': ['uri', 'bindName', 'baseDn'],
        },
    }
    try:
        jsonschema.validate(doc['value'], serversSchema)
    except jsonschema.ValidationError as e:
        raise ValidationException('Invalid LDAP servers list: ' + str(e))

    for server in doc['value']:
        if '://' not in server['uri']:
            server['uri'] = 'ldap://' + server['uri']
        server['password'] = server.get('password', '')
        server['searchField'] = server.get('searchField', 'uid')
        server['queryFilter'] = server.get('queryFilter', '')
