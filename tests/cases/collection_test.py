# -*- coding: utf-8 -*-
import json

from .. import base
from bson.objectid import ObjectId
from girder.constants import AccessType
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class CollectionTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        admin = {
            'email': 'admin@girder.test',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = User().createUser(**admin)

        user = {
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = User().createUser(**user)

        coll = {
            'name': 'Test Collection',
            'description': 'The description',
            'public': True,
            'creator': self.admin
        }
        self.collection = Collection().createCollection(**coll)

    def testEmptyCreator(self):
        c = Collection().createCollection('No Creator')
        self.assertEqual(c['creatorId'], None)

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
        resp = self.request(path='/collection/%s' % newCollId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_accessLevel'], AccessType.ADMIN)

        # Test collection update
        resp = self.request(path='/collection/%s' % newCollId,
                            method='PUT', user=self.admin,
                            params={'id': newCollId,
                                    'name': 'New collection name'})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], 'New collection name')

    def testDeleteCollection(self):
        # Requesting with no path should fail
        resp = self.request(path='/collection', method='DELETE', user=self.admin)
        self.assertStatus(resp, 400)

        # User without permission should not be able to delete collection
        resp = self.request(path='/collection/%s' % self.collection['_id'],
                            method='DELETE', user=self.user)
        self.assertStatus(resp, 403)

        # Admin user should be able to delete the collection
        resp = self.request(path='/collection/%s' % self.collection['_id'],
                            method='DELETE', user=self.admin)
        self.assertStatusOk(resp)

        coll = Collection().load(self.collection['_id'], force=True)
        self.assertEqual(coll, None)

    def testCollectionAccess(self):
        # Asking to change to an invalid access list should fail
        resp = self.request(path='/collection/%s/access' %
                            self.collection['_id'], method='PUT', params={
                                'access': 'not an access list',
                                'public': False
                            }, user=self.admin)
        self.assertStatus(resp, 400)

        # Create some folders underneath the collection
        folder1 = Folder().createFolder(
            parentType='collection', parent=self.collection, creator=self.admin,
            public=False, name='top level')
        folder2 = Folder().createFolder(
            parentType='folder', parent=folder1, creator=self.admin,
            public=False, name='subfolder')
        Folder().createFolder(
            parentType='collection', parent=self.collection, creator=self.admin,
            public=False, name='another top level folder')

        # Admin should see two top level folders
        resp = self.request(path='/collection/%s/details' % self.collection['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 2)
        self.assertNotIn('nItems', resp.json)

        # Normal user should see 0 folders
        resp = self.request(path='/collection/%s/details' % self.collection['_id'], user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 0)

        # Add read access on one of the folders
        Folder().setUserAccess(folder1, self.user, AccessType.READ, save=True)

        # Normal user should see one folder now
        resp = self.request(path='/collection/%s/details' % self.collection['_id'], user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nFolders'], 1)

        # Change the access to allow just the user
        obj = {'users': [{'id': str(self.user['_id']),
                          'level': AccessType.WRITE}]}
        resp = self.request(path='/collection/%s/access' %
                            self.collection['_id'], method='PUT', params={
                                'access': json.dumps(obj),
                                'public': True
                            }, user=self.admin)
        self.assertStatusOk(resp)

        # Request the collection access
        resp = self.request(path='/collection/%s/access' % self.collection['_id'], user=self.admin)
        self.assertStatusOk(resp)
        access = resp.json
        self.assertEqual(access['users'][0]['id'], str(self.user['_id']))
        self.assertEqual(access['users'][0]['level'], AccessType.WRITE)
        coll = Collection().load(self.collection['_id'], force=True)
        folder1 = Folder().load(folder1['_id'], force=True)
        folder2 = Folder().load(folder2['_id'], force=True)
        self.assertEqual(coll['public'], True)
        self.assertEqual(folder1['public'], False)

        # Update the collection recursively to public
        resp = self.request(
            path='/collection/%s/access' % coll['_id'], method='PUT', params={
                'access': json.dumps(obj),
                'public': True,
                'recurse': True,
                'progress': True
            }, user=self.admin)
        self.assertStatusOk(resp)
        coll = Collection().load(coll['_id'], force=True)
        folder1 = Folder().load(folder1['_id'], force=True)
        folder2 = Folder().load(folder2['_id'], force=True)
        self.assertEqual(coll['public'], True)
        self.assertEqual(folder1['public'], True)
        self.assertEqual(folder2['public'], True)
        self.assertEqual(folder1['access'], coll['access'])
        self.assertEqual(folder1['access'], folder2['access'])
        self.assertEqual(folder2['access'], {
            'users': [{
                'id': self.user['_id'],
                'level': AccessType.WRITE,
                'flags': []
            }],
            'groups': []
        })

        # Recursively drop the user's access level to READ
        obj['users'][0]['level'] = AccessType.READ
        resp = self.request(
            path='/collection/%s/access' % coll['_id'], method='PUT', params={
                'access': json.dumps(obj),
                'public': True,
                'recurse': True,
                'progress': True
            }, user=self.admin)
        self.assertStatusOk(resp)
        coll = Collection().load(coll['_id'], force=True)
        folder1 = Folder().load(folder1['_id'], force=True)
        folder2 = Folder().load(folder2['_id'], force=True)
        self.assertEqual(coll['public'], True)
        self.assertEqual(folder1['public'], True)
        self.assertEqual(folder2['public'], True)
        self.assertEqual(folder1['access'], coll['access'])
        self.assertEqual(folder1['access'], folder2['access'])
        self.assertEqual(folder2['access'], {
            'users': [{
                'id': self.user['_id'],
                'level': AccessType.READ,
                'flags': []
            }],
            'groups': []
        })

        # Recursively remove the user's access altogether, also make sure that
        # passing no "public" param just retains the current flag state
        obj['users'] = ()
        resp = self.request(
            path='/collection/%s/access' % coll['_id'], method='PUT', params={
                'access': json.dumps(obj),
                'recurse': True
            }, user=self.admin)
        self.assertStatusOk(resp)
        coll = Collection().load(coll['_id'], force=True)
        folder1 = Folder().load(folder1['_id'], force=True)
        folder2 = Folder().load(folder2['_id'], force=True)
        self.assertEqual(coll['public'], True)
        self.assertEqual(folder1['public'], True)
        self.assertEqual(folder2['public'], True)
        self.assertEqual(folder1['access'], coll['access'])
        self.assertEqual(folder1['access'], folder2['access'])
        self.assertEqual(folder2['access'], {
            'users': [],
            'groups': []
        })

        # Add group access to the collection
        group = Group().createGroup('test', self.admin)
        obj = {
            'groups': [{
                'id': str(group['_id']),
                'level': AccessType.WRITE
            }]
        }

        resp = self.request(
            path='/collection/%s/access' % coll['_id'], method='PUT', params={
                'access': json.dumps(obj),
                'recurse': False
            }, user=self.admin)
        self.assertStatusOk(resp)

        # Create a new top-level folder, it should inherit the collection ACL.
        resp = self.request(path='/folder', method='POST', params={
            'name': 'top level 2',
            'parentId': coll['_id'],
            'parentType': 'collection'
        }, user=self.admin)
        self.assertStatusOk(resp)
        folder = Folder().load(resp.json['_id'], force=True)
        coll = Collection().load(coll['_id'], force=True)
        self.assertEqual(coll['access']['users'], [])
        self.assertEqual(folder['access']['users'], [{
            'id': self.admin['_id'],
            'level': AccessType.ADMIN,
            'flags': []
        }])
        self.assertEqual(folder['access']['groups'], [{
            'id': group['_id'],
            'level': AccessType.WRITE,
            'flags': []
        }])
        self.assertEqual(folder['access']['groups'], coll['access']['groups'])

    def testCollectionCreatePolicy(self):
        # With default settings, non-admin users cannot create collections
        resp = self.request(path='/collection', method='POST', params={
            'name': 'user collection'
        }, user=self.user)
        self.assertStatus(resp, 403)

        # Allow any user to create collections
        Setting().set(SettingKey.COLLECTION_CREATE_POLICY, {
            'open': True
        })

        resp = self.request(path='/collection', method='POST', params={
            'name': 'open collection'
        }, user=self.user)
        self.assertStatusOk(resp)
        self.assertTrue('_id' in resp.json)

        # Anonymous users still shouldn't be able to
        resp = self.request(path='/collection', method='POST', params={
            'name': 'open collection'
        }, user=None)
        self.assertStatus(resp, 401)

        # Add a group that has collection create permission
        group = Group().createGroup(name='coll. creators', creator=self.admin)

        Setting().set(SettingKey.COLLECTION_CREATE_POLICY, {
            'open': False,
            'groups': [str(group['_id'])]
        })

        # Group membership should allow creation now
        Group().addUser(group=group, user=self.user)
        resp = self.request(path='/collection', method='POST', params={
            'name': 'group collection'
        }, user=self.user)
        self.assertStatusOk(resp)
        self.assertTrue('_id' in resp.json)

        # Test individual user access
        Group().removeUser(group=group, user=self.user)
        resp = self.request(path='/collection', method='POST', params={
            'name': 'group collection'
        }, user=self.user)
        self.assertStatus(resp, 403)

        Setting().set(SettingKey.COLLECTION_CREATE_POLICY, {
            'open': False,
            'users': [str(self.user['_id'])]
        })

        resp = self.request(path='/collection', method='POST', params={
            'name': 'user collection'
        }, user=self.user)
        self.assertStatusOk(resp)
        self.assertTrue('_id' in resp.json)

    def testMissingAclRefs(self):
        # Make fake user and group documents and put them into the
        # collection ACL.
        collModel = Collection()

        coll = collModel.setAccessList(
            self.collection, {
                'users': [{'id': ObjectId(), 'level': AccessType.READ}],
                'groups': [{'id': ObjectId(), 'level': AccessType.READ}]
            }, save=True)
        self.assertEqual(len(coll['access']['users']), 1)
        self.assertEqual(len(coll['access']['groups']), 1)

        # Bad refs should have been removed
        acl = collModel.getFullAccessList(coll)
        self.assertEqual(acl, {'users': [], 'groups': []})

        # Changes should have been saved to the database
        coll = collModel.load(coll['_id'], force=True)
        self.assertEqual(acl, coll['access'])
