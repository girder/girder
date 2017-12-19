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

import bson.json_util

from tests import base
from girder.constants import AccessType
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User


def setUpModule():
    base.enabledPlugins.append('mongo_search')
    base.startServer()


def tearDownModule():
    base.stopServer()


class MongoSearchTestCase(base.TestCase):

    def testMongoSearch(self):
        """
        Test resource/mongo_search endpoint
        """
        # Create a bunch of searchable documents
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        admin = User().createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        user = User().createUser(**user)

        coll1 = {
            'name': 'Test Collection',
            'description': 'magic words. And more magic.',
            'public': True,
            'creator': admin
        }
        coll1 = Collection().createCollection(**coll1)

        coll2 = {
            'name': 'Magic collection',
            'description': 'private',
            'public': False,
            'creator': admin
        }
        coll2 = Collection().createCollection(**coll2)
        Collection().setUserAccess(coll2, user, level=AccessType.READ, save=True)

        folder1 = {
            'parent': coll1,
            'parentType': 'collection',
            'name': 'Public test folder'
        }
        folder1 = Folder().createFolder(**folder1)
        Folder().setUserAccess(folder1, user, level=AccessType.READ, save=False)
        Folder().setPublic(folder1, True, save=True)

        folder2 = {
            'parent': coll2,
            'parentType': 'collection',
            'name': 'Private test folder'
        }
        folder2 = Folder().createFolder(**folder2)
        Folder().setUserAccess(folder2, user, level=AccessType.NONE, save=True)

        item1 = {
            'name': 'Public object',
            'creator': admin,
            'folder': folder1
        }
        item1 = Item().createItem(**item1)

        item2 = {
            'name': 'Secret object',
            'creator': admin,
            'folder': folder2
        }
        item2 = Item().createItem(**item2)

        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=user, params={
                'parentType': 'user',
                'parentId': user['_id'],
                'sort': 'name',
                'sortdir': 1
            })

        # First test all of the required parameters.
        self.ensureRequiredParams(
            path='/resource/search', required=['q', 'types'])

        # Now test parameter validation
        resp = self.request(path='/resource/mongo_search', params={
            'q': 'query',
            'type': 'wrong type'
        })
        self.assertStatus(resp, 400)
        self.assertEqual('Invalid resource type: wrong type', resp.json['message'])

        # Test validation of JSON input
        resp = self.request(path='/resource/mongo_search', params={
            'q': 'not_json',
            'type': 'folder'
        })
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'The query parameter must be a JSON object.')

        # Ensure searching respects permissions
        resp = self.request(path='/resource/mongo_search', params={
            'q': bson.json_util.dumps({'name': 'Private'}),
            'type': 'folder'
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request(path='/resource/mongo_search', params={
            'q': bson.json_util.dumps({'name': 'Private'}),
            'type': 'folder'
        }, user=user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertHasKeys(resp.json[0], ('_id', 'name', 'description'))
        self.assertEqual(len(resp.json[0]), 3)

        # Test item search
        resp = self.request(path='/resource/mongo_search', params={
            'q': bson.json_util.dumps({'folderId': folder1['_id']}),
            'type': 'item'
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [{
            '_id': str(item1['_id']),
            'name': 'Public object',
            'description': '',
            'folderId': str(folder1['_id'])
        }])

        resp = self.request(path='/resource/mongo_search', params={
            'q': bson.json_util.dumps({'folderId': folder2['_id']}),
            'type': 'item'
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request(path='/resource/mongo_search', params={
            'q': bson.json_util.dumps({'folderId': folder2['_id']}),
            'type': 'item'
        }, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [{
            '_id': str(item2['_id']),
            'name': 'Secret object',
            'description': '',
            'folderId': str(folder2['_id'])
        }])
