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

from tests import base
from girder.constants import AccessType


def setUpModule():
    base.enabledPlugins.append('provenance')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ProvenanceTestCase(base.TestCase):


    def ensureProvenanceResponse(self, resp, itemId, version, userId, eventType, meta):
        self.assertStatusOk(resp)
        itemProvenance = resp.json
        self.assertEqual(itemProvenance['itemId'], str(itemId))
        self.assertEqual(itemProvenance['provenance'][-1]['eventType'], eventType)
        self.assertEqual(str(itemProvenance['provenance'][-1]['version']), str(version))
        if eventType == 'creation':
            self.assertEqual(itemProvenance['provenance'][-1]['createdBy'], str(userId))
        else:
            self.assertEqual(itemProvenance['provenance'][-1]['updatedBy'], str(userId))
        provMetaEmpty = 'meta' not in itemProvenance['provenance'][-1] or len(itemProvenance['provenance'][-1]['meta']) == 0
        self.assertEqual(provMetaEmpty, len(meta) == 0)
        if not provMetaEmpty:
            # ensure keys and values are the same
            provMeta = itemProvenance['provenance'][-1]['meta']
            for key in provMeta.keys():
                self.assertEqual(provMeta[key], meta[key])
            for key in meta.keys():
                self.assertEqual(provMeta[key], meta[key])
    
    def getProvenanceRespAfterItemMetadataUpdate(self, item, meta, user):
        resp = self.request(path='/item/{}/metadata'.format(item['_id']),
                            method='PUT', user=user, body=json.dumps(meta),
                            type='application/json')
        
        resp = self.request(path='/item/{}/provenance'.format(item['_id']),
                            method='GET', user=user,
                            type='application/json')
        return resp



    def testProvenance(self):
        """
        Test provenance endpoint
        """
        # Create some test documents with an item
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        admin = self.model('user').createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        user = self.model('user').createUser(**user)

        coll1 = {
            'name': 'Test Collection',
            'description': 'test coll',
            'public': True,
            'creator': admin
        }
        coll1 = self.model('collection').createCollection(**coll1)

        folder1 = {
            'parent': coll1,
            'parentType': 'collection',
            'name': 'Public test folder'
        }
        folder1 = self.model('folder').createFolder(**folder1)
        self.model('folder').setUserAccess(
            folder1, user, level=AccessType.WRITE, save=False)
        self.model('folder').setPublic(folder1, True, save=True)

        folder2 = {
            'parent': coll1,
            'parentType': 'collection',
            'name': 'Private test folder'
        }
        folder2 = self.model('folder').createFolder(**folder2)
        self.model('folder').setUserAccess(
            folder2, user, level=AccessType.NONE, save=True)

        item1 = {
            'name': 'Public object',
            'creator': admin,
            'folder': folder1
        }
        item1 = self.model('item').createItem(**item1)

        # check that the first version of the item exists         
        resp = self.request(path='/item/{}/provenance'.format(item1['_id']),
                            method='GET', user=admin,
                            type='application/json')

        # ensure version 1, created by admin user, with creation event
        self.ensureProvenanceResponse(resp, item1['_id'], 1, admin['_id'], 'creation', {})

        # update meta to {x:y}
        metadata = {'x': 'y'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, admin)
        # ensure version 2, updated by admin user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 2, admin['_id'], 'update', metadata)
        
        # update meta to {} by regular user, we have to send in the key to remove it
        # but check the saved metadata against {}
        metadata = {'x': None}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 3, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 3, user['_id'], 'update', {})

        # update meta to {x:y} by regular user
        metadata = {'x': 'y'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 4, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 4, user['_id'], 'update', metadata)

        # update meta to {x:z} by regular user
        metadata = {'x': 'z'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 5, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 5, user['_id'], 'update', metadata)

        # update meta to {x:z, q:u} by regular user
        metadata = {'x': 'z', 'q': 'u'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 6, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 6, user['_id'], 'update', metadata)

        # update meta to {q:a} by regular user
        metadata = {'x': None, 'q': 'a'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 7, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 7, user['_id'], 'update', {'q':'a'})

        # update meta to {q:w} by regular user
        metadata = {'q': 'w'}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 8, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 8, user['_id'], 'update', metadata)

        # update meta to {a:b} by regular user
        metadata = {'a': 'b', 'q': None}
        resp = self.getProvenanceRespAfterItemMetadataUpdate(item1, metadata, user)
        # ensure version 9, updated by regular user, with update event, and meta in provenance matches
        self.ensureProvenanceResponse(resp, item1['_id'], 9, user['_id'], 'update', {'a': 'b'})


