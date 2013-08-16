#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

import cherrypy
import json

from .. import base

from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ItemTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        # Create a set of users so we can have some folders.
        self.users = [self.model('user').createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@u.com' % num)
            for num in [0, 1]]

        folders = self.model('folder').childFolders(
            self.users[0], 'user', user=self.users[0])
        (self.publicFolder, self.privateFolder) = folders

    def testItemCrud(self):
        """
        Test Create, Read, Update, and Delete of items.
        """
        self.ensureRequiredParams(
            path='/item', method='POST', required=('name', 'folderId'))

        # Attempt to create an item without write permission, should fail
        params = {
            'name': ' ',
            'description': ' a description ',
            'folderId': self.publicFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # Shouldn't be allowed to have an empty name
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertValidationError(resp, 'name')

        # Actually create the item in user 0's private folder
        params['name'] = ' my item name'
        params['folderId'] = self.privateFolder['_id']
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)

        item = resp.json
        self.assertEqual(item['name'], params['name'].strip())
        self.assertEqual(item['description'], params['description'].strip())

        # User 1 should not be able to see the item via find by folderId
        params = {
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='GET', user=self.users[1],
                            params=params)
        self.assertStatus(resp, 403)

        # Or by just requesting the item itself by ID
        resp = self.request(path='/item/%s' % str(item['_id']), method='GET',
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # User 0 should be able to see the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='GET',
                            user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], item['_id'])

        # Also from the children call
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])

        # User 1 should not be able to delete the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # User 0 should be able to delete the item
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[0])
        self.assertStatusOk(resp)

        item = self.model('item').load(item['_id'])
        self.assertEqual(item, None)
