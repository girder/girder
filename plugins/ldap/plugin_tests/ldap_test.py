# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the 'License' );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import ldap
import mock

from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.models.user import User
from tests import base

from girder_ldap.constants import PluginSettings


def setUpModule():
    base.enabledPlugins.append('ldap')
    base.startServer()


def tearDownModule():
    base.stopServer()


class MockLdap(object):
    def __init__(self, bindFail=False, searchFail=False, record=None):
        self.bindFail = bindFail
        self.searchFail = searchFail
        self.record = record

    def bind_s(self, *args, **kwargs):
        if self.bindFail:
            raise ldap.LDAPError({
                'desc': 'failed to connect'
            })

    def search_s(self, *args, **kwargs):
        if self.searchFail:
            return []

        return [(None, self.record or {
            'distinguishedName': [b'foobar'],
            'uid': [b'foobar'],
            'sn': [b'Bar'],
            'givenName': [b'Foo'],
            'mail': [b'foo@bar.com']
        })]

    def set_option(self, *args, **kwargs):
        pass

    def unbind_s(self, *args, **kwargs):
        pass


class LdapTestCase(base.TestCase):
    def testLdapLogin(self):
        settings = Setting()

        self.assertEqual(settings.get(PluginSettings.LDAP_SERVERS), [])

        with self.assertRaises(ValidationException):
            settings.set(PluginSettings.LDAP_SERVERS, {})

        settings.set(PluginSettings.LDAP_SERVERS, [{
            'baseDn': 'cn=Users,dc=foo,dc=bar,dc=org',
            'bindName': 'cn=foo,cn=Users,dc=foo,dc=bar,dc=org',
            'password': 'foo',
            'searchField': 'mail',
            'uri': 'foo.bar.org:389'
        }])

        with mock.patch('ldap.initialize', return_value=MockLdap()) as ldapInit:
            resp = self.request('/user/authentication', basicAuth='hello:world')
            self.assertEqual(len(ldapInit.mock_calls), 1)
            self.assertStatusOk(resp)

            # Register a new user
            user = resp.json['user']
            self.assertEqual(user['email'], 'foo@bar.com')
            self.assertEqual(user['firstName'], 'Foo')
            self.assertEqual(user['lastName'], 'Bar')
            self.assertEqual(user['login'], 'foobar')

            # Login as an existing user
            resp = self.request('/user/authentication', basicAuth='hello:world')
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['user']['_id'], user['_id'])

        with mock.patch('ldap.initialize', return_value=MockLdap(bindFail=True)):
            resp = self.request('/user/authentication', basicAuth='hello:world')
            self.assertStatus(resp, 401)

        with mock.patch('ldap.initialize', return_value=MockLdap(searchFail=True)):
            resp = self.request('/user/authentication', basicAuth='hello:world')
            self.assertStatus(resp, 401)

        # Test fallback to logging in with core auth
        normalUser = User().createUser(
            login='normal', firstName='Normal', lastName='User', email='normal@user.com',
            password='normaluser')
        with mock.patch('ldap.initialize', return_value=MockLdap(searchFail=True)):
            resp = self.request('/user/authentication', basicAuth='normal:normaluser')
            self.assertStatusOk(resp)
            self.assertEqual(str(normalUser['_id']), resp.json['user']['_id'])

        # Test registering from a record that only has a cn, no sn/givenName
        record = {
            'cn': [b'Fizz Buzz'],
            'mail': [b'fizz@buzz.com'],
            'distinguishedName': [b'shouldbeignored']
        }
        with mock.patch('ldap.initialize', return_value=MockLdap(record=record)):
            resp = self.request('/user/authentication', basicAuth='fizzbuzz:foo')
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['user']['login'], 'fizz')
            self.assertEqual(resp.json['user']['firstName'], 'Fizz')
            self.assertEqual(resp.json['user']['lastName'], 'Buzz')

        # Test falling back to other name generation behavior (first+last name)
        record = {
            'cn': [b'Fizz Buzz'],
            'mail': [b'fizz@buzz2.com'],
            'distinguishedName': [b'shouldbeignored']
        }
        with mock.patch('ldap.initialize', return_value=MockLdap(record=record)):
            resp = self.request('/user/authentication', basicAuth='fizzbuzz:foo')
            self.assertStatusOk(resp)
            self.assertEqual(resp.json['user']['login'], 'fizzbuzz')
            self.assertEqual(resp.json['user']['firstName'], 'Fizz')
            self.assertEqual(resp.json['user']['lastName'], 'Buzz')

    def testLdapStatusCheck(self):
        admin = User().createUser(
            login='admin', email='a@a.com', firstName='admin', lastName='admin',
            password='passwd', admin=True)

        params = {
            'bindName': 'cn=foo,cn=Users,dc=foo,dc=bar,dc=org',
            'password': 'foo',
            'uri': 'ldap://foo.bar.org:389'
        }

        with mock.patch('ldap.initialize', return_value=MockLdap(bindFail=True)):
            resp = self.request('/system/ldap_server/status', user=admin, params=params)
            self.assertStatusOk(resp)
            self.assertFalse(resp.json['connected'])
            self.assertEqual(resp.json['error'], 'LDAP connection error: failed to connect')

        with mock.patch('ldap.initialize', return_value=MockLdap(bindFail=False)):
            resp = self.request('/system/ldap_server/status', user=admin, params=params)
            self.assertStatusOk(resp)
            self.assertTrue(resp.json['connected'])
            self.assertNotIn('error', resp.json)
