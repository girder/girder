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
from girder.models.model_base import ValidationException
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter
from .constants import PluginSettings

_LDAP_ATTRS = ('uid', 'mail', 'cn', 'sn', 'givenName', 'distinguishedName')
_MAX_NAME_ATTEMPTS = 10
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
            return existing

    return _registerLdapUser(attrs, email)


def _ldapAuth(event):
    login, password = event.info['login'], event.info['password']

    # TODO cache LDAP servers list setting
    servers = ModelImporter.model('setting').get(PluginSettings.LDAP_SERVERS)

    for server in servers:
        # ldap requires a uri complete with protocol.
        # Append one if the user did not specify.
        uri = server['uri']
        if '://' not in uri:
            uri = 'ldap://' + uri
        conn = ldap.initialize(uri)
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
                # Try other LDAP servers or fall back to core auth
                conn.unbind_s()
                continue

            user = _getLdapUser(attrs)
            conn.unbind_s()
            if user:
                event.stopPropagation().preventDefault().addResponse(user)


@access.admin
@boundHandler()
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
    try:
        conn.bind_s(bindName, password, ldap.AUTH_SIMPLE)
        return {
            'connected': True
        }
    except ldap.LDAPError as e:
        return {
            'connected': False,
            'error': e.message.get('desc', 'Could not connect to server.')
        }
    finally:
        conn.unbind_s()


def load(info):
    events.bind('user_auth', info['name'], _ldapAuth)

    info['apiRoot'].system.route('GET', ('ldap_server', 'status'), _ldapServerTest)
