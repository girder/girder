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

from .. import base

from girder.constants import AccessType, ResourceRegistry
from girder.models.model_base import AccessControlledModel
from girder.utility.acl_mixin import AccessControlMixin


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class SearchTestCase(base.TestCase):

    def testResourceSearch(self):
        """
        Test resource/search endpoint
        """
        # get expected models from the database
        admin = self.model('user').findOne({'login': 'adminlogin'})
        user = self.model('user').findOne({'login': 'goodlogin'})
        coll1 = self.model('collection').findOne({'name': 'Test Collection'})
        coll2 = self.model('collection').findOne({'name': 'Magic collection'})
        item1 = self.model('item').findOne({'name': 'Public object'})

        # set user read permissions on the private collection
        self.model('collection').setUserAccess(
            coll2, user, level=AccessType.READ, save=True)

        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=user, params={
                'parentType': 'user',
                'parentId': user['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        privateFolder = resp.json[0]

        # First test all of the required parameters.
        self.ensureRequiredParams(
            path='/resource/search', required=['q', 'types'])

        # Now test parameter validation
        resp = self.request(path='/resource/search', params={
            'q': 'query',
            'types': ',,invalid;json!'
        })
        self.assertStatus(resp, 400)
        self.assertEqual('Parameter types must be valid JSON.', resp.json['message'])

        # Test searching with no results
        resp = self.request(path='/resource/search', params={
            'q': 'gibberish',
            'types': '["folder", "user", "collection", "group"]'
        })
        self.assertEqual(resp.json, {
            'folder': [],
            'user': [],
            'collection': [],
            'group': []
        })

        # Ensure searching respects permissions
        resp = self.request(path='/resource/search', params={
            'q': 'private',
            'types': '["folder", "user", "collection"]'
        })
        self.assertEqual(resp.json, {
            'folder': [],
            'user': [],
            'collection': []
        })

        resp = self.request(path='/resource/search', params={
            'q': 'pr',
            'mode': 'prefix',
            'types': '["folder", "user", "collection"]'
        })
        self.assertEqual(resp.json, {
            'folder': [],
            'user': [],
            'collection': []
        })

        resp = self.request(path='/resource/search', params={
            'q': 'private',
            'types': '["folder", "user", "collection"]'
        }, user=user)
        self.assertEqual(1, len(resp.json['folder']))
        self.assertDictContainsSubset({
            '_id': str(privateFolder['_id']),
            'name': 'Private'
        }, resp.json['folder'][0])
        self.assertEqual(1, len(resp.json['collection']))
        self.assertDictContainsSubset({
            '_id': str(coll2['_id']),
            'name': coll2['name']
        }, resp.json['collection'][0])
        self.assertEqual(0, len(resp.json['user']))

        resp = self.request(path='/resource/search', params={
            'q': 'pr',
            'mode': 'prefix',
            'types': '["folder", "user", "collection", "item"]'
        }, user=user)
        self.assertEqual(1, len(resp.json['folder']))
        self.assertDictContainsSubset({
            '_id': str(privateFolder['_id']),
            'name': 'Private'
        }, resp.json['folder'][0])
        self.assertEqual(0, len(resp.json['collection']))
        self.assertEqual(0, len(resp.json['item']))
        self.assertEqual(0, len(resp.json['user']))

        # Ensure that weights are respected, e.g. description should be
        # weighted less than name.
        resp = self.request(path='/resource/search', params={
            'q': 'magic',
            'types': '["collection"]'
        }, user=admin)
        self.assertEqual(2, len(resp.json['collection']))
        self.assertDictContainsSubset({
            '_id': str(coll2['_id']),
            'name': coll2['name']
        }, resp.json['collection'][0])
        self.assertDictContainsSubset({
            '_id': str(coll1['_id']),
            'name': coll1['name']
        }, resp.json['collection'][1])
        self.assertTrue(resp.json['collection'][0]['_textScore'] >
                        resp.json['collection'][1]['_textScore'])

        # Exercise user search by login
        resp = self.request(path='/resource/search', params={
            'q': 'goodlogin',
            'types': '["user"]'
        }, user=admin)
        self.assertEqual(1, len(resp.json['user']))
        self.assertDictContainsSubset({
            '_id': str(user['_id']),
            'firstName': user['firstName'],
            'lastName': user['lastName'],
            'login': user['login']
        }, resp.json['user'][0])

        # check item search with proper permissions
        resp = self.request(path='/resource/search', params={
            'q': 'object',
            'types': '["item"]'
        }, user=user)
        self.assertEqual(1, len(resp.json['item']))
        self.assertDictContainsSubset({
            '_id': str(item1['_id']),
            'name': item1['name']
        }, resp.json['item'][0])

        # Check search for model that is not access controlled
        self.assertNotIsInstance(
            self.model('assetstore'), AccessControlledModel)
        self.assertNotIsInstance(
            self.model('assetstore'), AccessControlMixin)
        ResourceRegistry.ALLOWED_SEARCH_MODE['prefix']['types'].add('assetstore')
        resp = self.request(path='/resource/search', params={
            'q': 'Test',
            'mode': 'prefix',
            'types': '["assetstore"]'
        }, user=user)
        self.assertEqual(1, len(resp.json['assetstore']))
