#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import jsonschema
import ldap
import six

from girder import events, logger
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler
from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.models.user import User
from girder.plugin import GirderPlugin
from girder.utility import setting_utilities

from .constants import PluginSettings

_LDAP_ATTRS = ('uid', 'mail', 'cn', 'sn', 'givenName', 'distinguishedName')
_MAX_NAME_ATTEMPTS = 10
_CONNECT_TIMEOUT = 4  # seconds
_serversSchema = {
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


@setting_utilities.default(PluginSettings.LDAP_SERVERS)
def _defaultServers():
    return []


@setting_utilities.validator(PluginSettings.LDAP_SERVERS)
def _validateLdapServers(doc):
    try:
        jsonschema.validate(doc['value'], _serversSchema)
    except jsonschema.ValidationError as e:
        raise ValidationException('Invalid LDAP servers list: ' + e.message)

    for server in doc['value']:
        if '://' not in server['uri']:
            server['uri'] = 'ldap://' + server['uri']
        server['password'] = server.get('password', '')
        server['searchField'] = server.get('searchField', 'uid')


def _registerLdapUser(attrs, email, server):
    first, last = None, None
    if attrs.get('givenName'):
        first = attrs['givenName'][0].decode('utf8')
    elif attrs.get('cn'):
        first = attrs['cn'][0].decode('utf8').split()[0]

    if attrs.get('sn'):
        last = attrs['sn'][0].decode('utf8')
    elif attrs.get('cn'):
        last = attrs['cn'][0].decode('utf8').split()[-1]

    if not first or not last:
        raise Exception('No LDAP name entry found for %s.' % email)

    # Try using the search field value as the login. If it's an email address,
    # use the part before the @.
    try:
        login = attrs[server['searchField']][0].decode('utf8').split('@')[0]
        return User().createUser(
            login, password=None, firstName=first, lastName=last, email=email)
    except ValidationException as e:
        if e.field != 'login':
            raise

    # Fall back to deriving login from user's name
    for i in six.moves.range(_MAX_NAME_ATTEMPTS):
        login = ''.join((first, last, str(i) if i else ''))
        try:
            return User().createUser(
                login, password=None, firstName=first, lastName=last, email=email)
        except ValidationException as e:
            if e.field != 'login':
                raise

    raise Exception('Failed to generate login name for LDAP user %s.' % email)


def _getLdapUser(attrs, server):
    emails = attrs.get('mail')
    if not emails:
        raise Exception('No email record present for the given LDAP user.')

    if not isinstance(emails, (list, tuple)):
        emails = (emails,)

    emails = [e.decode('utf8').lower() for e in emails]
    existing = User().find({
        'email': {'$in': emails}
    }, limit=1)
    if existing.count():
        return existing.next()

    return _registerLdapUser(attrs, emails[0], server)


def _ldapAuth(event):
    login, password = event.info['login'], event.info['password']
    servers = Setting().get(PluginSettings.LDAP_SERVERS)

    for server in servers:
        try:
            # ldap requires a uri complete with protocol.
            # Append one if the user did not specify.
            conn = ldap.initialize(server['uri'])
            conn.set_option(ldap.OPT_TIMEOUT, _CONNECT_TIMEOUT)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, _CONNECT_TIMEOUT)
            conn.bind_s(server['bindName'], server['password'], ldap.AUTH_SIMPLE)

            searchStr = '%s=%s' % (server['searchField'], login)
            # Add the searchStr to the attributes, keep local scope.
            lattr = _LDAP_ATTRS + (server['searchField'],)
            results = conn.search_s(server['baseDn'], ldap.SCOPE_SUBTREE, searchStr, lattr)
            if results:
                entry, attrs = results[0]
                dn = attrs['distinguishedName'][0].decode('utf8')
                try:
                    conn.bind_s(dn, password, ldap.AUTH_SIMPLE)
                except ldap.LDAPError:
                    # Try other LDAP servers or fall back to core auth
                    continue
                finally:
                    conn.unbind_s()

                user = _getLdapUser(attrs, server)
                if user:
                    event.stopPropagation().preventDefault().addResponse(user)
        except ldap.LDAPError:
            logger.exception('LDAP connection exception (%s).' % server['uri'])
            continue


@access.admin
@boundHandler
@autoDescribeRoute(
    Description('Test connection status to a LDAP server.')
    .notes('You must be an administrator to call this.')
    .param('uri', 'The URI of the server.')
    .param('bindName', 'The LDAP identity to bind with.')
    .param('password', 'Password to bind with.')
    .errorResponse('You are not an administrator.', 403)
)
def _ldapServerTest(self, uri, bindName, password, params):
    conn = ldap.initialize(uri)
    conn.set_option(ldap.OPT_TIMEOUT, _CONNECT_TIMEOUT)
    conn.set_option(ldap.OPT_NETWORK_TIMEOUT, _CONNECT_TIMEOUT)

    try:
        conn.bind_s(bindName, password, ldap.AUTH_SIMPLE)
        return {
            'connected': True
        }
    except ldap.LDAPError as e:
        return {
            'connected': False,
            'error': 'LDAP connection error: ' + e.args[0].get('desc', 'failed to connect')
        }
    finally:
        conn.unbind_s()


class LDAPPlugin(GirderPlugin):
    DISPLAY_NAME = 'LDAP authentication'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        events.bind('model.user.authenticate', 'ldap', _ldapAuth)
        info['apiRoot'].system.route('GET', ('ldap_server', 'status'), _ldapServerTest)
