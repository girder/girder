# -*- coding: utf-8 -*-
import json

from .. import base

from girder.api.v1 import resource
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel
from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.item import Item
from girder.models.user import User
from girder.utility.acl_mixin import AccessControlMixin
from girder.utility import search


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
        admin = User().findOne({'login': 'adminlogin'})
        user = User().findOne({'login': 'goodlogin'})
        coll1 = Collection().findOne({'name': 'Test Collection'})
        coll2 = Collection().findOne({'name': 'Magic collection'})
        item1 = Item().findOne({'name': 'Public object'})

        # set user read permissions on the private collection
        Collection().setUserAccess(coll2, user, level=AccessType.READ, save=True)

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
        self.ensureRequiredParams(path='/resource/search', required=['q', 'types'])

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
        self.assertStatusOk(resp)
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
        self.assertStatusOk(resp)
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
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            'folder': [],
            'user': [],
            'collection': []
        })

        resp = self.request(path='/resource/search', params={
            'q': 'private',
            'types': '["folder", "user", "collection"]'
        }, user=user)
        self.assertStatusOk(resp)
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
        self.assertStatusOk(resp)
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
        self.assertStatusOk(resp)
        self.assertEqual(2, len(resp.json['collection']))
        self.assertDictContainsSubset({
            '_id': str(coll2['_id']),
            'name': coll2['name']
        }, resp.json['collection'][0])
        self.assertDictContainsSubset({
            '_id': str(coll1['_id']),
            'name': coll1['name']
        }, resp.json['collection'][1])
        self.assertTrue(resp.json['collection'][0]['_textScore']
                        > resp.json['collection'][1]['_textScore'])

        # Exercise user search by login
        resp = self.request(path='/resource/search', params={
            'q': 'goodlogin',
            'types': '["user"]'
        }, user=admin)
        self.assertStatusOk(resp)
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
        self.assertStatusOk(resp)
        self.assertEqual(1, len(resp.json['item']))
        self.assertDictContainsSubset({
            '_id': str(item1['_id']),
            'name': item1['name']
        }, resp.json['item'][0])

        # Check search for model that is not access controlled
        self.assertNotIsInstance(Assetstore(), AccessControlledModel)
        self.assertNotIsInstance(Assetstore(), AccessControlMixin)
        resource.allowedSearchTypes.add('assetstore')
        resp = self.request(path='/resource/search', params={
            'q': 'Test',
            'mode': 'prefix',
            'types': '["assetstore"]'
        }, user=user)
        self.assertStatusOk(resp)
        self.assertEqual(1, len(resp.json['assetstore']))

    def testResourceFileSearch(self):
        admin = User().findOne({'login': 'adminlogin'})

        resp = self.request(path='/resource/search', params={
            'q': 'public',
            'types': '["file"]'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['file']), 1)
        resp = self.request(path='/resource/search', params={
            'q': 'personal',
            'types': '["file"]'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['file']), 0)
        resp = self.request(path='/resource/search', params={
            'q': 'file',
            'types': '["file"]'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['file']), 1)
        resp = self.request(path='/resource/search', params={
            'q': 'personal',
            'types': '["file"]'
        }, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['file']), 1)
        resp = self.request(path='/resource/search', params={
            'q': 'file',
            'types': '["file"]'
        }, user=admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['file']), 2)

    def testSearchModeRegistry(self):
        def testSearchHandler(query, types, user, level, limit, offset):
            return {
                'query': query,
                'types': types
            }

        search.addSearchMode('testSearch', testSearchHandler)

        # Use the new search mode.
        resp = self.request(path='/resource/search', params={
            'q': 'Test',
            'mode': 'testSearch',
            'types': json.dumps(['collection'])
        })
        self.assertStatusOk(resp)
        self.assertDictEqual(resp.json, {
            'query': 'Test',
            'types': ['collection']
        })

        search.removeSearchMode('testSearch')

        # Use the deleted search mode.
        resp = self.request(path='/resource/search', params={
            'q': 'Test',
            'mode': 'testSearch',
            'types': json.dumps(['collection'])
        })
        self.assertStatus(resp, 400)
