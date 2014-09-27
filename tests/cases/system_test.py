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

import json

from .. import base

from girder.api.describe import API_VERSION
from girder.constants import SettingKey, SettingDefault


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class SystemTestCase(base.TestCase):
    """
    Contains tests of the /system API endpoints.
    """

    def testGetVersion(self):
        resp = self.request(path='/system/version', method='GET')
        self.assertEqual(resp.json['apiVersion'], API_VERSION)

    def testSettings(self):
        users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

        # Only admins should be able to get or set settings
        for method in ('GET', 'PUT', 'DELETE'):
            resp = self.request(path='/system/setting', method=method, params={
                'key': 'foo',
                'value': 'bar'
            }, user=users[1])
            self.assertStatus(resp, 403)

        # Only valid setting keys should be allowed
        obj = ['foo', 'bar', 'baz']
        resp = self.request(path='/system/setting', method='PUT', params={
            'key': 'foo',
            'value': json.dumps(obj)
        }, user=users[0])
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['field'], 'key')

        # Only a valid JSON list is permitted
        resp = self.request(path='/system/setting', method='PUT', params={
            'list': json.dumps('not_a_list')
        }, user=users[0])
        self.assertStatus(resp, 400)

        # Set a valid setting key
        resp = self.request(path='/system/setting', method='PUT', params={
            'key': SettingKey.PLUGINS_ENABLED,
            'value': json.dumps(obj)
        }, user=users[0])
        self.assertStatusOk(resp)

        # We should now be able to retrieve it
        resp = self.request(path='/system/setting', method='GET', params={
            'key': SettingKey.PLUGINS_ENABLED
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, obj)

        # We should now clear the setting
        resp = self.request(path='/system/setting', method='DELETE', params={
            'key': SettingKey.PLUGINS_ENABLED
        }, user=users[0])
        self.assertStatusOk(resp)

        # Setting should now be ()
        setting = self.model('setting').get(SettingKey.PLUGINS_ENABLED)
        self.assertEqual(setting, [])

        # We should be able to ask for a different default
        setting = self.model('setting').get(SettingKey.PLUGINS_ENABLED,
                                            default=None)
        self.assertEqual(setting, None)

        # We should also be able to put several setting using a JSON list
        resp = self.request(path='/system/setting', method='PUT', params={
            'list': json.dumps([
                {'key': SettingKey.PLUGINS_ENABLED, 'value': json.dumps(obj)},
                {'key': SettingKey.COOKIE_LIFETIME, 'value': None},
            ])
        }, user=users[0])
        self.assertStatusOk(resp)

        # We can get a list as well
        resp = self.request(path='/system/setting', method='GET', params={
            'list': json.dumps([
                SettingKey.PLUGINS_ENABLED,
                SettingKey.COOKIE_LIFETIME,
            ])
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[SettingKey.PLUGINS_ENABLED], obj)

        # We can get the default values, or ask for no value if the current
        # value is taken from the default
        resp = self.request(path='/system/setting', method='GET', params={
            'key': SettingKey.PLUGINS_ENABLED,
            'default': 'default'
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request(path='/system/setting', method='GET', params={
            'key': SettingKey.COOKIE_LIFETIME,
            'default': 'none'
        }, user=users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

        # But we have to ask for a sensible value in teh default parameter
        resp = self.request(path='/system/setting', method='GET', params={
            'key': SettingKey.COOKIE_LIFETIME,
            'default': 'bad_value'
        }, user=users[0])
        self.assertStatus(resp, 400)

        # Try to set each key in turn to test the validation.  First test with
        # am invalid value, then test with the default value.  If the value
        # 'bad' won't trigger a validation error, the key should be present in
        # the badValues table.
        badValues = {
            SettingKey.EMAIL_FROM_ADDRESS: '',
            SettingKey.SMTP_HOST: '',
        }
        for key in SettingDefault.defaults:
            resp = self.request(path='/system/setting', method='PUT', params={
                'key': key,
                'value': badValues.get(key, 'bad')
            }, user=users[0])
            self.assertStatus(resp, 400)
            resp = self.request(path='/system/setting', method='PUT', params={
                'key': key,
                'value': SettingDefault.defaults[key]
            }, user=users[0])
            self.assertStatusOk(resp)
