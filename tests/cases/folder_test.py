# -*- coding: utf-8 -*-
import datetime
import json

from .. import base

from girder import events
from girder.constants import AccessType, SortDir
from girder.models.notification import Notification, ProgressState
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.user import User


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class FolderTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        users = ({
            'email': 'good@girder.test',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }, {
            'email': 'regularuser@girder.test',
            'login': 'regularuser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        })
        self.admin, self.user = [User().createUser(**user) for user in users]

    def testLegacyFolders(self):
        folder = Folder().createFolder(
            parent=self.admin, parentType='user', creator=self.admin,
            name='LegacyFolder')

        del folder['meta']
        folder = Folder().save(folder)
        assert 'meta' not in folder

        folder = Folder().load(folder['_id'], user=self.admin)
        assert 'meta' in folder

    def testChildFolders(self):
        # Test with some bad parameters
        resp = self.request(path='/folder', method='GET', params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid search mode.')

        resp = self.request(path='/folder', method='GET', params={
            'parentType': 'invalid',
            'parentId': self.admin['_id']
        })
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Invalid value for parentType: "invalid". Allowed values: folder, user, collection.')

        # We should only be able to see the public folder if we are anonymous
        resp = self.request(path='/folder', method='GET', params={
            'parentType': 'user',
            'parentId': self.admin['_id']
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        # Test GET on the result folder
        resp = self.request(path='/folder/%s' % str(resp.json[0]['_id']))
        self.assertStatusOk(resp)
        self.assertIsInstance(resp.json, dict)
        self.assertFalse('access' in resp.json)

        # If we log in as the user, we should also be able to see the
        # private folder. Also test that our sortdir param works.
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': SortDir.DESCENDING
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]['name'], 'Public')
        self.assertEqual(resp.json[1]['name'], 'Private')
        publicFolder = resp.json[0]
        privateFolder = resp.json[1]

        # Change properties of a folder
        resp = self.request(
            path='/folder/%s' % publicFolder['_id'], method='PUT',
            user=self.admin, params={
                'name': 'New name ',
                'description': ' A description '
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], 'New name')
        self.assertEqual(resp.json['description'], 'A description')

        # Move should fail with a bogus parent
        resp = self.request(
            path='/folder/%s' % publicFolder['_id'], method='PUT',
            user=self.admin, params={
                'parentType': 'badParent',
                'parentId': privateFolder['_id']
            })
        self.assertStatus(resp, 400)

        # Move the public folder underneath the private folder
        resp = self.request(
            path='/folder/%s' % publicFolder['_id'], method='PUT',
            user=self.admin, params={
                'parentType': 'folder',
                'parentId': privateFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentCollection'], 'folder')
        self.assertEqual(resp.json['parentId'], privateFolder['_id'])
        self.assertEqual(resp.json['name'], 'New name')

        # Move should fail if we don't have write permission on the
        # destination parent
        publicFolder = Folder().load(publicFolder['_id'], force=True)
        publicFolder = Folder().setUserAccess(publicFolder, self.user, AccessType.WRITE, save=True)
        resp = self.request(
            path='/folder/%s' % publicFolder['_id'], method='PUT',
            user=self.user, params={
                'parentId': self.admin['_id'],
                'parentType': 'user'
            })
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['message'].startswith(
            'Write access denied for user'))

    def testFolderTextSearch(self):
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'text': 'Public',
                'sortdir': SortDir.DESCENDING
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)

    def testCreateFolder(self):
        self.ensureRequiredParams(
            path='/folder', method='POST', required=['name', 'parentId'],
            user=self.admin)

        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        privateFolder = resp.json[0]
        publicFolder = resp.json[1]

        self.assertEqual(privateFolder['name'], 'Private')
        self.assertEqual(publicFolder['name'], 'Public')

        # Try to create a folder as anonymous; should fail
        resp = self.request(path='/folder', method='POST', params={
            'name': 'a folder',
            'parentId': publicFolder['_id']
        })
        self.assertStatus(resp, 401)

        # Try to create a folder with a bogus parent; should fail
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentType': 'badParent',
                'parentId': publicFolder['_id']
            })
        self.assertStatus(resp, 400)

        # Try to create a folder with a blank name; should fail
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' ',
                'parentId': publicFolder['_id']
            })
        self.assertStatus(resp, 400)

        # Actually create subfolder under Public
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentId'], publicFolder['_id'])
        self.assertEqual(resp.json['parentCollection'], 'folder')
        self.assertTrue(resp.json['public'])
        folder = Folder().load(resp.json['_id'], force=True)
        self.assertTrue(Folder().hasAccess(folder, self.admin, AccessType.ADMIN))

        # Now fetch the children of Public, we should see it
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'folder',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'My public subfolder')

        # Try to create a folder with same name
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertValidationError(resp, 'name')

        # Create a folder in the user
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': 'New User Folder',
                'parentType': 'user',
                'parentId': str(self.admin['_id'])
            })
        self.assertStatus(resp, 200)
        assert 'meta' in resp.json

    def testReuseExisting(self):
        self.ensureRequiredParams(
            path='/folder', method='POST', required=['name', 'parentId'],
            user=self.admin)

        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        publicFolder = resp.json[1]

        # Actually create subfolder under Public
        newFolder = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(newFolder)

        # Try to create a folder with same name, reuseExisting flag not set
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertValidationError(resp, 'name')

        # Create folder with same name, reuseExisting flag set
        reuseFolder = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id'],
                'reuseExisting': True
            })
        self.assertStatusOk(reuseFolder)
        self.assertEqual(newFolder.json['_id'], reuseFolder.json['_id'])

    def testFolderMetadataDirect(self):
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        self.assertStatusOk(resp)
        publicFolder = resp.json[1]

        # Actually create subfolder under Public
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id'],
                'metadata': 'invalid json'
            })
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Parameter metadata must be valid JSON.')

        metadata = {
            'foo': 'bar',
            'test': 2
        }
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder with meta',
                'parentId': publicFolder['_id'],
                'metadata': json.dumps(metadata)}
        )
        self.assertStatusOk(resp)
        folder = resp.json
        self.assertEqual(folder['meta']['foo'], metadata['foo'])
        self.assertEqual(folder['meta']['test'], metadata['test'])

        metadata = {
            'foo': None,
            'test': 3,
            'bar': 'baz'
        }
        resp = self.request(
            path='/folder/{_id}'.format(**folder), method='PUT',
            user=self.admin, params={'metadata': json.dumps(metadata)}
        )
        self.assertStatusOk(resp)
        folder = resp.json
        self.assertNotHasKeys(folder['meta'], ['foo'])
        self.assertEqual(folder['meta']['test'], metadata['test'])
        self.assertEqual(folder['meta']['bar'], metadata['bar'])

    def testFolderMetadataCrud(self):
        """
        Test CRUD of metadata on folders
        """
        # Grab the default user folders
        resp = self.request(
            path='/folder', method='GET', user=self.admin, params={
                'parentType': 'user',
                'parentId': self.admin['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        self.assertStatusOk(resp)
        publicFolder = resp.json[1]

        # Actually create subfolder under Public
        resp = self.request(
            path='/folder', method='POST', user=self.admin, params={
                'name': ' My public subfolder  ',
                'parentId': publicFolder['_id']
            })
        self.assertStatusOk(resp)
        folder = resp.json

        # Test that bad json fails
        resp = self.request(path='/folder/%s/metadata' % folder['_id'],
                            method='PUT', user=self.admin,
                            body='badJSON', type='application/json')
        self.assertStatus(resp, 400)

        # Add some metadata
        metadata = {
            'foo': 'bar',
            'test': 2
        }
        resp = self.request(path='/folder/%s/metadata' % folder['_id'],
                            method='PUT', user=self.admin,
                            body=json.dumps(metadata), type='application/json')

        folder = resp.json
        self.assertEqual(folder['meta']['foo'], metadata['foo'])
        self.assertEqual(folder['meta']['test'], metadata['test'])

        # Edit and remove metadata
        metadata['test'] = None
        metadata['foo'] = 'baz'
        resp = self.request(path='/folder/%s/metadata' % folder['_id'],
                            method='PUT', user=self.admin,
                            body=json.dumps(metadata), type='application/json')

        folder = resp.json
        self.assertEqual(folder['meta']['foo'], metadata['foo'])
        self.assertNotHasKeys(folder['meta'], ['test'])

        # Make sure metadata cannot be added if there is a period in the key
        # name
        metadata = {
            'foo.bar': 'notallowed'
        }
        resp = self.request(path='/folder/%s/metadata' % folder['_id'],
                            method='PUT', user=self.admin,
                            body=json.dumps(metadata), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Invalid key foo.bar: keys must not contain the "." character.')

        # Make sure metadata cannot be added if the key begins with a $
        metadata = {
            '$foobar': 'alsonotallowed'
        }
        resp = self.request(path='/folder/%s/metadata' % folder['_id'],
                            method='PUT', user=self.admin,
                            body=json.dumps(metadata), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Invalid key $foobar: keys must not start with the "$" character.')

        # Test allowNull
        metadata = {
            'foo': None
        }
        resp = self.request(
            path='/folder/%s/metadata' % folder['_id'], params={'allowNull': True},
            user=self.admin, method='PUT', body=json.dumps(metadata), type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['meta'], metadata)

        # Test delete metadata endpoint
        resp = self.request(
            path='/folder/%s/metadata' % folder['_id'], user=self.admin, method='DELETE',
            body=json.dumps(['foo']), type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['meta'], {})

    def testDeleteFolder(self):
        cbInfo = {}

        # Hook into model deletion with kwargs event to test it
        def cb(event):
            cbInfo['kwargs'] = event.info['kwargs']
            cbInfo['doc'] = event.info['document']

        with events.bound('model.folder.remove_with_kwargs', 'test', cb):

            # Requesting with no path should fail
            resp = self.request(path='/folder', method='DELETE',
                                user=self.admin)
            self.assertStatus(resp, 400)

            # Grab one of the user's top level folders
            folders = Folder().childFolders(
                parent=self.admin, parentType='user', user=self.admin, limit=1,
                sort=[('name', SortDir.DESCENDING)])
            folderResp = next(folders)

            # Add a subfolder and an item to that folder
            subfolder = Folder().createFolder(
                folderResp, 'sub', parentType='folder', creator=self.admin)
            item = Item().createItem('item', creator=self.admin, folder=subfolder)

            self.assertTrue('_id' in subfolder)
            self.assertTrue('_id' in item)

            # Delete the folder
            resp = self.request(path='/folder/%s' % folderResp['_id'],
                                method='DELETE', user=self.admin, params={
                                    'progress': 'true'
            })
            self.assertStatusOk(resp)

            # Make sure the folder, its subfolder, and its item were all deleted
            folder = Folder().load(folderResp['_id'], force=True)
            subfolder = Folder().load(subfolder['_id'], force=True)
            item = Item().load(item['_id'])

            self.assertEqual(folder, None)
            self.assertEqual(subfolder, None)
            self.assertEqual(item, None)

            # Make sure progress record exists and that it is set to expire soon
            notifs = list(Notification().get(self.admin))
            self.assertEqual(len(notifs), 1)
            self.assertEqual(notifs[0]['type'], 'progress')
            self.assertEqual(notifs[0]['data']['state'], ProgressState.SUCCESS)
            self.assertEqual(notifs[0]['data']['title'],
                             'Deleting folder Public')
            self.assertEqual(notifs[0]['data']['message'], 'Done')
            self.assertEqual(notifs[0]['data']['total'], 3)
            self.assertEqual(notifs[0]['data']['current'], 3)
            self.assertTrue(notifs[0]['expires'] < datetime.datetime.utcnow()
                            + datetime.timedelta(minutes=1))

            # Make sure our event handler was called with expected args
            self.assertTrue('kwargs' in cbInfo)
            self.assertTrue('doc' in cbInfo)
            self.assertTrue('progress' in cbInfo['kwargs'])
            self.assertEqual(cbInfo['doc']['_id'], folderResp['_id'])

    def testCleanFolder(self):
        folder = next(Folder().childFolders(
            parent=self.admin, parentType='user', user=self.admin, limit=1,
            sort=[('name', SortDir.DESCENDING)]))

        # Add some data under the folder
        subfolder = Folder().createFolder(
            folder, 'sub', parentType='folder', creator=self.admin)
        item = Item().createItem('item', creator=self.admin, folder=folder)
        subitem = Item().createItem('item', creator=self.admin, folder=subfolder)

        # Clean the folder contents
        resp = self.request(path='/folder/%s/contents' % folder['_id'],
                            method='DELETE', user=self.admin, params={
                                'progress': 'true'
        })
        self.assertStatusOk(resp)

        # Make sure the subfolder and items were deleted, but that the top
        # folder still exists.
        old, folder = folder, Folder().load(folder['_id'], force=True)
        subfolder = Folder().load(subfolder['_id'], force=True)
        item = Item().load(item['_id'])
        subitem = Item().load(subitem['_id'])

        self.assertTrue('_id' in folder)
        self.assertEqual(folder, old)
        self.assertEqual(subfolder, None)
        self.assertEqual(item, None)
        self.assertEqual(subitem, None)

    def testLazyFieldComputation(self):
        """
        Demonstrate that a folder that is saved in the database without
        derived fields (like lowerName or baseParentId) get those values
        computed at load() time.
        """
        folder = Folder().createFolder(
            parent=self.admin, parentType='user', creator=self.admin,
            name=' My Folder Name')

        self.assertEqual(folder['lowerName'], 'my folder name')
        self.assertEqual(folder['baseParentType'], 'user')

        # Force the item to be saved without lowerName and baseParentType
        # fields
        del folder['lowerName']
        del folder['baseParentType']
        folder = Folder().save(folder, validate=False)

        folder = Folder().find({'_id': folder['_id']})[0]
        self.assertNotHasKeys(folder, ('lowerName', 'baseParentType'))

        # Now ensure that calling load() actually populates those fields and
        # saves the results persistently
        Folder().load(folder['_id'], force=True)
        folder = Folder().find({'_id': folder['_id']})[0]
        self.assertHasKeys(folder, ('lowerName', 'baseParentType'))
        self.assertEqual(folder['lowerName'], 'my folder name')
        self.assertEqual(folder['baseParentType'], 'user')
        self.assertEqual(folder['baseParentId'], self.admin['_id'])

    def testParentsToRoot(self):
        """
        Demonstrate that forcing parentsToRoot will cause it to skip the
        filtering process.
        """
        userFolder = Folder().createFolder(
            parent=self.admin, parentType='user', creator=self.admin,
            name=' My Folder Name')

        # Filtering adds the _accessLevel key to the object
        # So forcing should result in an absence of that key
        parents = Folder().parentsToRoot(userFolder, force=True)
        for parent in parents:
            self.assertNotIn('_accessLevel', parent['object'])

        parents = Folder().parentsToRoot(userFolder)
        for parent in parents:
            self.assertIn('_accessLevel', parent['object'])

        # The logic is a bit different for user/collection parents,
        # so we need to handle the other case
        subFolder = Folder().createFolder(
            parent=userFolder, parentType='folder', creator=self.admin,
            name=' My Subfolder Name')

        parents = Folder().parentsToRoot(subFolder, force=True)
        for parent in parents:
            self.assertNotIn('_accessLevel', parent['object'])

        parents = Folder().parentsToRoot(subFolder, user=self.admin)
        for parent in parents:
            self.assertIn('_accessLevel', parent['object'])

    def testFolderAccessAndDetails(self):
        # create a folder to work with
        folder = Folder().createFolder(
            parent=self.admin, parentType='user', creator=self.admin,
            name='Folder')

        resp = self.request(
            path='/folder/%s/access' % folder['_id'], method='GET',
            user=self.admin)
        self.assertStatusOk(resp)
        access = resp.json
        self.assertEqual(access, {
            'users': [{
                'login': self.admin['login'],
                'level': AccessType.ADMIN,
                'id': str(self.admin['_id']),
                'flags': [],
                'name': '%s %s' % (
                    self.admin['firstName'], self.admin['lastName'])}],
            'groups': []
        })
        self.assertTrue(not folder.get('public'))
        # Setting the access list with bad json should throw an error
        resp = self.request(
            path='/folder/%s/access' % folder['_id'], method='PUT',
            user=self.admin, params={'access': 'badJSON'})
        self.assertStatus(resp, 400)
        # Change the access to public
        resp = self.request(
            path='/folder/%s/access' % folder['_id'], method='PUT',
            user=self.admin,
            params={'access': json.dumps(access), 'public': True})
        self.assertStatusOk(resp)
        resp = self.request(
            path='/folder/%s' % folder['_id'], method='GET',
            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['public'], True)

        # Create an item in the folder
        Item().createItem(folder=folder, creator=self.admin, name='Item')
        # Create a public and private folder within the folder
        Folder().createFolder(
            parent=folder, parentType='folder', creator=self.admin,
            name='Public', public=True)
        Folder().createFolder(
            parent=folder, parentType='folder', creator=self.admin,
            name='Private', public=False)

        # Test folder details as anonymous
        resp = self.request(
            path='/folder/%s/details' % str(folder['_id']))
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nItems'], 1)
        self.assertEqual(resp.json['nFolders'], 1)

        # Test folder details as admin
        resp = self.request(
            path='/folder/%s/details' % str(folder['_id']), user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['nItems'], 1)
        self.assertEqual(resp.json['nFolders'], 2)

    def testFolderCopy(self):
        # create a folder with a subfolder, items, and metadata
        mainFolder = Folder().createFolder(
            parent=self.admin, parentType='user', creator=self.admin,
            name='Main Folder')
        subFolder = Folder().createFolder(
            parent=mainFolder, parentType='folder', creator=self.admin,
            name='Sub Folder')
        mainItem = Item().createItem('Main Item', creator=self.admin, folder=mainFolder)
        subItem = Item().createItem('Sub Item', creator=self.admin, folder=subFolder)
        metadata = {'key': 'value'}
        resp = self.request(
            path='/folder/%s/metadata' % mainFolder['_id'], method='PUT',
            user=self.admin, body=json.dumps(metadata),
            type='application/json')
        self.assertStatusOk(resp)
        # Add a file under the main item to test size reporting
        size = 5
        self.uploadFile(
            name='test.txt', contents='.' * size, user=self.admin,
            parent=mainItem, parentType='item')
        mainFolder = Folder().load(mainFolder['_id'], force=True)
        self.assertEqual(mainFolder['size'], size)

        # Now copy the folder alongside itself
        resp = self.request(
            path='/folder/%s/copy' % mainFolder['_id'], method='POST',
            user=self.admin)
        self.assertStatusOk(resp)
        # Check our new folder information
        newFolder = resp.json
        self.assertEqual(newFolder['name'], 'Main Folder (1)')
        self.assertEqual(newFolder['size'], size)

        # Check the copied item inside the new folder
        resp = self.request('/item', user=self.admin, params={
            'folderId': newFolder['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'Main Item')
        self.assertEqual(resp.json[0]['size'], size)

        # Check copied folder metadata
        resp = self.request(
            path='/folder/%s' % newFolder['_id'], method='GET',
            user=self.admin, type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['meta'], metadata)
        # Check for the item, subfolder, and subfolder item
        resp = self.request(
            path='/folder', method='GET',
            params={'parentType': 'folder', 'parentId': str(newFolder['_id'])},
            user=self.admin, type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        newSub = resp.json[0]
        self.assertEqual(newSub['name'], subFolder['name'])
        self.assertNotEqual(str(newSub['_id']), str(subFolder['_id']))
        resp = self.request(
            path='/item', method='GET',
            params={'folderId': str(newFolder['_id'])},
            user=self.admin, type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        newItem = resp.json[0]
        self.assertEqual(newItem['name'], mainItem['name'])
        self.assertNotEqual(str(newItem['_id']), str(mainItem['_id']))
        resp = self.request(
            path='/item', method='GET',
            params={'folderId': str(newSub['_id'])},
            user=self.admin, type='application/json')
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        newSubItem = resp.json[0]
        self.assertEqual(newSubItem['name'], subItem['name'])
        self.assertNotEqual(str(newSubItem['_id']), str(subItem['_id']))
        # Test copying the subFolder
        resp = self.request(
            path='/folder/%s/copy' % subFolder['_id'], method='POST',
            user=self.admin, params={'public': 'original', 'progress': True})
        self.assertStatusOk(resp)
        # Check our new folder name
        newSubFolder = resp.json
        self.assertEqual(newSubFolder['name'], 'Sub Folder (1)')
        # Test that a bogus parentType throws an error
        resp = self.request(
            path='/folder/%s/copy' % subFolder['_id'], method='POST',
            user=self.admin, params={'parentType': 'badValue'})
        self.assertStatus(resp, 400)
        # Test that when we copy a folder into itself we don't recurse
        resp = self.request(
            path='/folder/%s/copy' % subFolder['_id'], method='POST',
            user=self.admin, params={
                'progress': True,
                'parentType': 'folder',
                'parentId': str(subFolder['_id'])})
        self.assertStatusOk(resp)

        # Test copying with public set to False
        resp = self.request(
            path='/folder/%s/copy' % subFolder['_id'], method='POST',
            user=self.admin, params={'public': 'false', 'progress': True})
        self.assertStatusOk(resp)

    def testUpdateDuplicatedName(self):
        folder1 = Folder().createFolder(
            name='foo', parent=self.admin, parentType='user', creator=self.admin)
        folder2 = Folder().createFolder(
            name='bar', parent=self.admin, parentType='user', creator=self.admin)
        folder2['name'] = 'foo'
        Folder().save(folder2, validate=False)
        self.assertEqual(folder2['name'], 'foo')
        folder1['size'] = 3
        Folder().save(folder1)
        self.assertEqual(folder1['name'], 'foo')
