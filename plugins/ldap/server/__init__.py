import ldap
import six

from girder import events, logger
from girder.api.rest import AccessException
from girder.models.model_base import ValidationException
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter
from .constants import PluginSettings

_LDAP_ATTRS = ('uid', 'mail', 'cn', 'sn', 'givenName', 'distinguishedName')
_MAX_NAME_ATTEMPTS = 10


@setting_utilities.default(PluginSettings.LDAP_SERVERS)
def _defaultServers():
    return []


@setting_utilities.validator(PluginSettings.LDAP_SERVERS)
def _validateLdapServers(doc):
    if not isinstance(doc['value'], (list, tuple)):
        raise ValidationException('LDAP servers must be a list.')

    for server in doc['value']:
        if not server.get('uri'):
            raise ValidationException('LDAP servers must contain a uri.')

        if not server.get('bindName'):
            raise ValidationException('LDAP servers must contain a bindName.')

        if 'baseDn' not in server:
            raise ValidationException('LDAP servers must contain a baseDn.')

        server['password'] = server.get('password', '')
        server['searchField'] = server.get('searchField', 'uid')


def _registerLdapUser(attrs, email):
    first, last = None, None
    if attrs.get('givenName'):
        first = attrs['givenName'][0]
    elif attrs.get('cn'):
        first = attrs['cn'][0].split()[0]

    if attrs.get('sn'):
        last = attrs['sn'][0]
    elif attrs.get('cn'):
        last = attrs['cn'][0].split()[-1]

    if not first or not last:
        raise Exception('No LDAP name entry found for %s.' % email)

    for i in six.moves.range(_MAX_NAME_ATTEMPTS):
        login = ''.join((first, last, str(i) if i else ''))
        try:
            return ModelImporter.model('user').createUser(
                login, password=None, firstName=first, lastName=last, email=email)
        except ValidationException as e:
            if e.field != 'login':
                raise

    raise Exception('Failed to generate login name for LDAP user %s.' % email)


def _getLdapUser(attrs):
    emails = attrs.get('mail')
    if not emails:
        raise Exception('No email record present for the given LDAP user.')

    if not isinstance(emails, (list, tuple)):
        emails = (emails,)

    userModel = ModelImporter.model('user')
    for email in emails:
        existing = userModel.findOne({
            'email': {'$eq': email.lower()}
        })
        if existing:
            if existing['salt']:
                # This user has a password stored in girder, we fall back to core auth
                return None
            return existing

    return _registerLdapUser(attrs, email)


def _ldapAuth(event):
    login, password = event.info['login'], event.info['password']

    # TODO cache LDAP servers list setting
    servers = ModelImporter.model('setting').get(PluginSettings.LDAP_SERVERS)

    for server in servers:
        conn = ldap.initialize(server['uri'])
        try:
            conn.bind_s(server['bindName'], server['password'], ldap.AUTH_SIMPLE)
        except ldap.LDAPError:
            logger.exception('LDAP connection failed (%s).' % server['uri'])
            continue

        searchStr = '%s=%s' % (server['searchField'], login)
        results = conn.search_s(server['baseDn'], ldap.SCOPE_ONELEVEL, searchStr, _LDAP_ATTRS)

        if results:
            entry, attrs = results[0]
            try:
                conn.bind_s(attrs['distinguishedName'][0], password, ldap.AUTH_SIMPLE)
            except ldap.LDAPError:
                conn.unbind_s()
                raise AccessException('Login failed.')

            user = _getLdapUser(attrs)
            if user:
                event.stopPropagation().preventDefault().addResponse(user)


def load(info):
    events.bind('user_auth', info['name'], _ldapAuth)
