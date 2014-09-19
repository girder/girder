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

import json

from .. import base

from girder.constants import AccessType


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class CollectionTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        admin = {
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = self.model('user').createUser(**user)

        coll = {
            'name': 'Test Collection',
            'description': 'The description',
            'public': True,
            'creator': self.admin
        }
        self.collection = self.model('collection').createCollection(**coll)

    def testCreateAndListCollections(self):
        self.ensureRequiredParams(
            path='/collection', method='POST', required=['name'],
            user=self.admin)

        # Try to create a collection anonymously; should fail
        resp = self.request(path='/collection', method='POST', params={
            'name': 'new collection'
        })
        self.assertStatus(resp, 401)

        # Try to create a collection as non-admin user; should fail
        resp = self.request(path='/collection', method='POST', params={
            'name': 'new collection'
        }, user=self.user)
        self.assertStatus(resp, 403)

        # Create the collection as the admin user, make it private
        resp = self.request(path='/collection', method='POST', params={
            'name': '  New collection  ',
            'description': '  my description ',
            'public': 'false'
        }, user=self.admin)
        self.assertStatusOk(resp)
        newCollId = resp.json['_id']

        # Now attempt to list the collections as anonymous user
        resp = self.request(path='/collection')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], self.collection['name'])

        # Admin user should see both collections
        resp = self.request(path='/collection', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['name'], 'New collection')
        self.assertEqual(resp.json[0]['description'], 'my description')
        self.assertEqual(resp.json[1]['name'], self.collection['name'])

        # Test text search
        resp = self.request(path='/collection', user=self.admin, params={
            'text': 'new'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], newCollId)
        self.assertEqual(resp.json[0]['name'], 'New collection')

        # Test collection get
        resp = self.request(path='/collection/{}'.format(newCollId),
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_accessLevel'], AccessType.ADMIN)

        # Test collection update
        resp = self.request(path='/collection/{}'.format(newCollId),
                            method='PUT', user=self.admin,
                            params={'id': newCollId,
                                    'name': 'New collection name'})
        self.assertStatusOk(resp)

    def testDeleteCollection(self):
        # Requesting with no path should fail
        resp = self.request(path='/collection', method='DELETE',
                            user=self.admin)
        self.assertStatus(resp, 400)

        # User without permission should not be able to delete collection
        resp = self.request(path='/collection/%s' % self.collection['_id'],
                            method='DELETE', user=self.user)
        self.assertStatus(resp, 403)

        # Admin user should be able to delete the collection
        resp = self.request(path='/collection/%s' % self.collection['_id'],
                            method='DELETE', user=self.admin)
        self.assertStatusOk(resp)

        coll = self.model('collection').load(self.collection['_id'], force=True)
        self.assertEqual(coll, None)

    def testCollectionAccess(self):
        # Asking to change to  an invalid access list should fail
        resp = self.request(path='/collection/%s/access' %
                            self.collection['_id'], method='PUT', params={
                                'access': 'not an access list',
                                'public': False
                            }, user=self.admin)
        self.assertStatus(resp, 400)

        # Change the access to allow just the user
        obj = {'users': [{'id': str(self.user['_id']),
                          'level': AccessType.WRITE}]}
        resp = self.request(path='/collection/%s/access' %
                            self.collection['_id'], method='PUT', params={
                                'access': json.dumps(obj),
                                'public': False
                            }, user=self.admin)
        self.assertStatusOk(resp)

        # Request the collection access
        resp = self.request(path='/collection/%s/access' %
                            self.collection['_id'], user=self.admin)
        self.assertStatusOk(resp)
        access = resp.json
        self.assertEqual(access['users'][0]['id'], str(self.user['_id']))
        self.assertEqual(access['users'][0]['level'], AccessType.WRITE)
