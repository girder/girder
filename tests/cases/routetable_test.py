#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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
import os

from .. import base
from girder.constants import GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID, SettingKey
from girder.models.user import User


def setUpModule():
    base.mockPluginDir(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_plugins'))
    base.enabledPlugins.append('has_webroot')
    base.startServer()


def tearDownModule():
    base.stopServer()


class RouteTableTestCase(base.TestCase):
    def setUp(self):
        super(RouteTableTestCase, self).setUp()

        self.admin = User().createUser(
            email='admin@email.com', login='admin', firstName='Admin',
            lastName='Admin', password='password', admin=True)

    def testRouteTableSettings(self):
        # Test Girder not having a route
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({})
        }, method='PUT', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Girder and static root must be routable.')

        # Test static not having a route
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/'})
        }, method='PUT', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Girder and static root must be routable.')

        # Test duplicate routes
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/some_route',
                                 GIRDER_STATIC_ROUTE_ID: '/static',
                                 'other': '/some_route'})
        }, method='PUT', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Routes must be unique.')

        # Test invalid routes
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/',
                                 GIRDER_STATIC_ROUTE_ID: '/static',
                                 'other': 'route_without_a_leading_slash'})
        }, method='PUT', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Routes must begin with a forward slash.')

        # This is already set by default, this just verifies the endpoint is working
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/',
                                 GIRDER_STATIC_ROUTE_ID: '/static',
                                 'has_webroot': '/has_webroot'})
        }, method='PUT', user=self.admin)
        self.assertStatusOk(resp)

        resp = self.request('/has_webroot', prefix='', isJson=False, appPrefix='/has_webroot')
        self.assertStatusOk(resp)
        self.assertTrue('some webroot' in self.getBody(resp))

        # girder should be at /
        resp = self.request('/', prefix='', isJson=False)
        self.assertStatusOk(resp)
        self.assertTrue('g-global-info-apiroot' in self.getBody(resp))

        # has_webroot is mounted on /has_weboort
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE
        }, user=self.admin)
        self.assertStatusOk(resp)
        self.assertTrue('has_webroot' in resp.json)
        self.assertEqual(resp.json['has_webroot'], '/has_webroot')

        # has_webroot is set to be mounted on /has_webroot even after removing it from the list of
        # enabled plugins.
        base.enabledPlugins.remove('has_webroot')
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE
        }, user=self.admin)
        self.assertStatusOk(resp)
        self.assertTrue('has_webroot' in resp.json)
        self.assertEqual(resp.json['has_webroot'], '/has_webroot')
        base.enabledPlugins.append('has_webroot')

        # Only when has_webroot has been explicitly removed by the user is its route table entry
        # cleared.
        resp = self.request('/system/plugins', params={
            'plugins': json.dumps([
                plugin for plugin in base.enabledPlugins if plugin != 'has_webroot'])
        }, method='PUT', user=self.admin)
        self.assertStatusOk(resp)

        # now, confirm that the plugin's route table entry has actually been removed
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE
        }, user=self.admin)
        self.assertStatusOk(resp)
        self.assertTrue('has_webroot' not in resp.json)

        # Setting the static route to http should be allowed
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/',
                                 GIRDER_STATIC_ROUTE_ID: 'http://127.0.0.1/static'})
        }, method='PUT', user=self.admin)
        self.assertStatusOk(resp)
        # but not to a relative path
        resp = self.request('/system/setting', params={
            'key': SettingKey.ROUTE_TABLE,
            'value': json.dumps({GIRDER_ROUTE_ID: '/',
                                 GIRDER_STATIC_ROUTE_ID: 'relative/static'})
        }, method='PUT', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Static root must begin with a forward slash or contain a URL scheme.')
