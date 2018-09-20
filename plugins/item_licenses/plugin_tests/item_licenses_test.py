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

import six

from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User
from tests import base

from girder_item_licenses.constants import PluginSettings


def setUpModule():
    base.enabledPlugins.append('item_licenses')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ItemLicensesTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        # Create a user
        user = {
            'email': 'user1@email.com',
            'login': 'user1login',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'user1password',
            'admin': False
        }
        self.user = User().createUser(**user)

        # Get user's private folder
        folders = Folder().childFolders(self.user, 'user', user=self.user)
        for folder in folders:
            if folder['name'] == 'Private':
                self.folder = folder
                break

    def testItemCreateInvalid(self):
        """
        Test creating items with invalid licenses.
        """
        # Create item with a null name
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id'],
            'license': None
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertValidationError(resp, 'license')

        # Create item with an invalid license name
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id'],
            'license': 'Unsupported license'
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertValidationError(resp, 'license')

        # Create item with a valid license name with extra whitespace
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id'],
            'license': ' The MIT License (MIT) '
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertValidationError(resp, 'license')

    def testItemCreateAndUpdate(self):
        """
        Test creating, reading, and updating an item, especially with regards to
        its license field.
        """
        # Create item without specifying a license
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], '')

        # Create item with a blank license name
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id'],
            'license': ''
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], '')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], '')

        # Update item license
        params = {
            'license': 'Apache License 2'
        }
        resp = self.request(path='/item/%s' % resp.json['_id'], method='PUT',
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

        # Update item license to be unspecified
        params = {
            'license': ''
        }
        resp = self.request(path='/item/%s' % resp.json['_id'], method='PUT',
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], '')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], '')

        # Create item with a valid license name
        params = {
            'name': ' my item name',
            'description': ' a description ',
            'folderId': self.folder['_id'],
            'license': 'The MIT License (MIT)'
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'The MIT License (MIT)')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'The MIT License (MIT)')

        # Update item
        params = {
            'name': 'changed name',
            'description': 'new description',
            'license': 'Apache License 2'
        }
        resp = self.request(path='/item/%s' % resp.json['_id'], method='PUT',
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

        # Update item with the same license name
        params = {
            'license': 'Apache License 2'
        }
        resp = self.request(path='/item/%s' % resp.json['_id'], method='PUT',
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

    def testItemCopy(self):
        """
        Test copying an item, especially with regards to its license field.
        """
        params = {
            'name': 'original item',
            'description': 'original description',
            'license': 'The MIT License (MIT)',
            'folderId': self.folder['_id']
        }

        # Create item
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.user)
        self.assertStatusOk(resp)
        origItemId = resp.json['_id']

        # Copy to a new item with different name and license.
        params = {
            'name': 'new item',
            'license': 'Apache License 2'
        }
        resp = self.request(path='/item/%s/copy' % origItemId,
                            method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

        # Fetch item
        resp = self.request(path='/item/%s' % resp.json['_id'],
                            params=params, user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['license'], 'Apache License 2')

    def testGetLicenses(self):
        """
        Test getting list of licenses.
        """
        # Get default settings
        resp = self.request(path='/item/licenses', user=self.user, params={
            'default': True
        })
        self.assertStatusOk(resp)
        self.assertGreater(len(resp.json), 1)
        self.assertIn('category', resp.json[0])
        self.assertIn('licenses', resp.json[0])
        self.assertGreater(len(resp.json[0]['licenses']), 8)
        self.assertIn('name', resp.json[0]['licenses'][0])
        self.assertGreater(len(resp.json[0]['licenses'][0]['name']), 0)
        self.assertIn('name', resp.json[0]['licenses'][1])
        self.assertGreater(len(resp.json[0]['licenses'][1]['name']), 0)

        # Get current settings
        resp = self.request(path='/item/licenses', user=self.user)
        self.assertStatusOk(resp)
        self.assertGreater(len(resp.json), 1)
        self.assertIn('category', resp.json[0])
        self.assertIn('licenses', resp.json[0])
        self.assertGreater(len(resp.json[0]['licenses']), 8)
        self.assertIn('name', resp.json[0]['licenses'][0])
        self.assertGreater(len(resp.json[0]['licenses'][0]['name']), 0)
        self.assertIn('name', resp.json[0]['licenses'][1])
        self.assertGreater(len(resp.json[0]['licenses'][1]['name']), 0)

        # Change licenses
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': [{'name': '1'}]},
             {'category': 'B', 'licenses': [{'name': '2'}, {'name': '3'}]}])

        # Get default settings after changing licenses
        resp = self.request(path='/item/licenses', user=self.user, params={
            'default': True
        })
        self.assertStatusOk(resp)
        self.assertStatusOk(resp)
        self.assertGreater(len(resp.json), 1)
        self.assertIn('category', resp.json[0])
        self.assertIn('licenses', resp.json[0])
        self.assertGreater(len(resp.json[0]['licenses']), 8)
        self.assertIn('name', resp.json[0]['licenses'][0])
        self.assertGreater(len(resp.json[0]['licenses'][0]['name']), 0)
        self.assertIn('name', resp.json[0]['licenses'][1])
        self.assertGreater(len(resp.json[0]['licenses'][1]['name']), 0)

        # Get current settings after changing licenses
        resp = self.request(path='/item/licenses', user=self.user)
        self.assertStatusOk(resp)
        six.assertCountEqual(
            self, resp.json,
            [{'category': 'A', 'licenses': [{'name': '1'}]},
             {'category': 'B', 'licenses': [{'name': '2'}, {'name': '3'}]}])

    def testLicensesSettingValidation(self):
        """
        Test validation of licenses setting.
        """
        # Test valid settings
        Setting().set(
            PluginSettings.LICENSES,
            [])
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': []}])
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': [{'name': '1'}]}])
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': [{'name': '1'}, {'name': '2'}]}])
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': []},
             {'category': 'B', 'licenses': [{'name': '1'}]}])
        Setting().set(
            PluginSettings.LICENSES,
            [{'category': 'A', 'licenses': []},
             {'category': 'B', 'licenses': [{'name': '1'}, {'name': '2'}]}])

        # Test invalid top-level types
        for val in (None, 1, '', {}, [{}]):
            self.assertRaises(ValidationException, Setting().set, PluginSettings.LICENSES, val)

        # Test invalid category types
        for category, licenses in ((None, []), (1, []), ('', []), ({}, [])):
            self.assertRaises(
                ValidationException,
                Setting().set,
                PluginSettings.LICENSES,
                [{'category': category, 'licenses': licenses}])

        # Test invalid licenses types
        for val in (None, {}, [1], ['']):
            self.assertRaises(
                ValidationException,
                Setting().set,
                PluginSettings.LICENSES,
                [{'category': 'A', 'licenses': val}])

        # Test invalid license names
        for val in (None, 1, '', {}, []):
            self.assertRaises(
                ValidationException,
                Setting().set,
                PluginSettings.LICENSES,
                [{'category': 'A', 'licenses': [{'name': val}]}])
