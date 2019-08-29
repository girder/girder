import jsonschema

from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    SERVERS = 'ldap.servers'


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
                'uri': {
                    'type': 'string',
                    'minLength': 1
                },
                'bindName': {
                    'type': 'string',
                    'minLength': 1
                },
                'baseDn': {
                    'type': 'string'
                }
            },
            'required': ['uri', 'bindName', 'baseDn']
        }
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
