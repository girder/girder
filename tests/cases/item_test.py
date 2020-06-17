# -*- coding: utf-8 -*-
import os
import io
import itertools
import json
import shutil
import zipfile

from .. import base

from girder.constants import AccessType
from girder.models.assetstore import Assetstore
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.token import Token
from girder.models.user import User


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ItemTestCase(base.TestCase):

    def setUp(self):
        super().setUp()

        # Create a set of users so we can have some folders.
        self.users = [User().createUser(
            'usr%s' % num, 'passwd', 'tst', 'usr', 'u%s@girder.test' % num)
            for num in [0, 1]]

        folders = Folder().childFolders(self.users[0], 'user', user=self.users[0])
        for folder in folders:
            if folder['name'] == 'Public':
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        self.assetstore = Assetstore().getCurrent()
        root = self.assetstore['root']

        # Clean out the test assetstore on disk
        shutil.rmtree(root)

        # First clean out the temp directory
        tmpdir = os.path.join(root, 'temp')
        if os.path.isdir(tmpdir):
            for tempname in os.listdir(tmpdir):
                os.remove(os.path.join(tmpdir, tempname))

    def _createItem(self, parentId, name, description, user):
        params = {
            'name': name,
            'description': description,
            'folderId': parentId
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=user)
        self.assertStatusOk(resp)
        assert 'meta' in resp.json
        return resp.json

    def _testUploadFileToItem(self, item, name, user, contents):
        """
        Uploads a non-empty file to the server.
        """
        # Initialize the upload
        resp = self.request(
            path='/file', method='POST', user=user, params={
                'parentType': 'item',
                'parentId': item['_id'],
                'name': name,
                'size': len(contents)
            })
        self.assertStatusOk(resp)

        uploadId = resp.json['_id']

        # Send the first chunk
        resp = self.request(
            path='/file/chunk', method='POST', body=contents, user=user, params={
                'uploadId': uploadId
            }, type='application/octet-stream')
        self.assertStatusOk(resp)

    def _testDownloadSingleFileItem(self, item, user, contents):
        """
        Downloads a single-file item from the server
        :param item: The item to download.
        :type item: dict
        :param contents: The expected contents.
        :type contents: str
        """
        resp = self.request(path='/item/%s/download' % item['_id'],
                            method='GET', user=user, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(contents, self.getBody(resp))
        self.assertEqual(resp.headers['Content-Disposition'],
                         'attachment; filename="file_1"')

        # Test downloading the item with contentDisposition=inline.
        params = {'contentDisposition': 'inline'}
        resp = self.request(path='/item/%s/download' % item['_id'],
                            method='GET', user=user, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(contents, self.getBody(resp))
        self.assertEqual(resp.headers['Content-Disposition'],
                         'inline; filename="file_1"')

        # Test downloading with an offset
        resp = self.request(path='/item/%s/download' % item['_id'],
                            method='GET', user=user, isJson=False,
                            params={'offset': 1})
        self.assertStatus(resp, 206)

        self.assertEqual(contents[1:], self.getBody(resp))

    def _testDownloadMultiFileItem(self, item, user, contents, format=None):
        params = None
        if format:
            params = {'format': format}
        resp = self.request(path='/item/%s/download' % item['_id'],
                            method='GET', user=user, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        zipFile = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)),
                                  'r')
        prefix = os.path.split(zipFile.namelist()[0])[0]
        expectedZip = {}
        for name in contents:
            expectedZip[os.path.join(prefix, name)] = contents[name]
        self.assertHasKeys(expectedZip, zipFile.namelist())
        self.assertHasKeys(zipFile.namelist(), expectedZip)
        for name in zipFile.namelist():
            expected = expectedZip[name]
            if not isinstance(expected, bytes):
                expected = expected.encode('utf8')
            self.assertEqual(expected, zipFile.read(name))

    def testLegacyItems(self):
        folder = Folder().createFolder(
            parent=self.users[0], parentType='user', creator=self.users[0],
            name='New Folder')
        item = Item().createItem(
            name='LegacyItem',
            creator=self.users[0],
            folder=folder)

        del item['meta']
        item = Item().save(item)
        assert 'meta' not in item

        item = Item().load(item['_id'], user=self.users[0])
        assert 'meta' in item

    def testItemDownloadAndChildren(self):
        curItem = self._createItem(self.publicFolder['_id'],
                                   'test_for_download', 'fake description',
                                   self.users[0])
        self._testUploadFileToItem(curItem, 'file_1', self.users[0], 'foobar')

        self._testDownloadSingleFileItem(curItem, self.users[0], 'foobar')
        self._testDownloadMultiFileItem(curItem, self.users[0],
                                        {'file_1': 'foobar'}, format='zip')

        self._testUploadFileToItem(curItem, 'file_2', self.users[0], 'foobz')

        resp = self.request(path='/item/%s/files' % curItem['_id'],
                            method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['name'], 'file_1')
        self.assertEqual(resp.json[1]['name'], 'file_2')
        self.assertEqual(resp.json[0]['size'], 6)
        self.assertEqual(resp.json[1]['size'], 5)

        self._testDownloadMultiFileItem(curItem, self.users[0],
                                        {'file_1': 'foobar', 'file_2': 'foobz'})

    def testItemCrud(self):
        """
        Test Create, Read, Update, and Delete of items.
        """
        self.ensureRequiredParams(
            path='/item', method='POST', required=('folderId',),
            user=self.users[1])

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
        self.assertEqual(resp.json['_modelType'], 'item')

        # Also from the children call
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])

        # Test finding the item using a text string with and without a folderId
        params['text'] = 'my item name'
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])

        del params['folderId']
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])

        # A limit should work
        params['limit'] = 1
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item['_id'])
        # An offset should give us nothing
        params['offset'] = 1
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)

        # Finding should fail with no parameters
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params={})
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'Invalid search mode.')

        # Test update of the item
        params = {
            'name': 'changed name',
            'description': 'new description'
        }
        resp = self.request(path='/item/%s' % item['_id'], method='PUT',
                            params=params, user=self.users[0])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], params['name'])
        self.assertEqual(resp.json['description'], params['description'])

        # Test moving an item to the public folder
        item = Item().load(item['_id'], force=True)
        self.assertFalse(Item().hasAccess(item))
        resp = self.request(path='/item/%s' % item['_id'], method='PUT',
                            user=self.users[0], params={
                                'folderId': self.publicFolder['_id']})
        self.assertStatusOk(resp)
        item = Item().load(resp.json['_id'], force=True)
        self.assertTrue(Item().hasAccess(item))

        # Move should fail if we don't have write permission on the
        # destination folder
        self.publicFolder = Folder().setUserAccess(
            self.publicFolder, self.users[1], AccessType.WRITE, save=True)
        resp = self.request(path='/item/%s' % item['_id'], method='PUT',
                            user=self.users[1], params={
                                'folderId': self.privateFolder['_id']})
        self.assertStatus(resp, 403)
        self.assertTrue(resp.json['message'].startswith(
            'Write access denied for folder'))

        # Try to update/PUT without an id
        resp = self.request(path='/item/', method='PUT',
                            params=params, user=self.users[0])
        self.assertStatus(resp, 400)

        # Try a bad endpoint (should 400)
        resp = self.request(path='/item/%s/blurgh' % item['_id'],
                            method='GET',
                            user=self.users[1])
        self.assertStatus(resp, 400)

        # Try delete with no ID (should 400)
        resp = self.request(path='/item/', method='DELETE', user=self.users[1])
        self.assertStatus(resp, 400)

        # User 1 should not be able to delete the item with read access
        self.publicFolder = Folder().setUserAccess(
            self.publicFolder, self.users[1], AccessType.READ, save=True)
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[1])
        self.assertStatus(resp, 403)

        # User 1 should be able to delete the item with write access
        self.publicFolder = Folder().setUserAccess(
            self.publicFolder, self.users[1], AccessType.WRITE, save=True)
        resp = self.request(path='/item/%s' % str(item['_id']), method='DELETE',
                            user=self.users[1])
        self.assertStatusOk(resp)

        # Verify that the item is deleted
        item = Item().load(item['_id'])
        self.assertEqual(item, None)

    def testItemMetadataDirect(self):
        params = {
            'name': 'item with metadata via POST',
            'description': ' a description ',
            'folderId': self.privateFolder['_id'],
            'metadata': 'not JSON'
        }
        resp = self.request(
            path='/item', method='POST', params=params, user=self.users[0])
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Parameter metadata must be valid JSON.')

        # Add some metadata
        metadata = {
            'foo': 'bar',
            'test': 2
        }
        params['metadata'] = json.dumps(metadata)
        resp = self.request(
            path='/item', method='POST', params=params, user=self.users[0])
        self.assertStatusOk(resp)
        item = resp.json
        self.assertEqual(item['meta']['foo'], metadata['foo'])
        self.assertEqual(item['meta']['test'], metadata['test'])

        metadata = {
            'foo': None,
            'test': 3,
            'bar': 'baz'
        }
        resp = self.request(
            path='/item/{_id}'.format(**item), method='PUT',
            user=self.users[0], params={'metadata': json.dumps(metadata)}
        )
        self.assertStatusOk(resp)
        item = resp.json
        self.assertNotHasKeys(item['meta'], ['foo'])
        self.assertEqual(item['meta']['test'], metadata['test'])
        self.assertEqual(item['meta']['bar'], metadata['bar'])

    def testItemMetadataCrud(self):
        """
        Test CRUD of metadata.
        """
        # Create an item
        params = {
            'name': 'item with metadata',
            'description': ' a description ',
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)
        item = resp.json

        # Try to delete metadata from an item that doesn't have any set on it
        # yet.
        resp = self.request(path='/item/%s/metadata' % (item['_id']),
                            method='DELETE', user=self.users[0],
                            body=json.dumps(['foobar']), type='application/json')
        item = resp.json
        self.assertStatusOk(resp)
        self.assertEqual(item['meta'], {})

        # Add some metadata
        metadata = {
            'foo': 'bar',
            'test': 2
        }
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['foo'], metadata['foo'])
        self.assertEqual(item['meta']['test'], metadata['test'])

        # Test invalid JSON constants
        body = '{"key": {"foo": Infinity}}'
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=body, type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Error: "Infinity" is not valid JSON.')

        # Edit and remove metadata
        metadata['test'] = None
        metadata['foo'] = 'baz'
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['foo'], metadata['foo'])
        self.assertNotHasKeys(item['meta'], ['test'])

        # Test insertion of null values
        metadata['nullVal'] = None
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), params={'allowNull': True},
                            type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['nullVal'], None)

        # Adding an unrelated key should not affect existing keys
        del metadata['nullVal']
        metadata['other'] = 'macguffin'
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')

        item = resp.json
        self.assertEqual(item['meta']['other'], metadata['other'])
        self.assertEqual(item['meta']['nullVal'], None)

        # Test metadata deletion
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='DELETE', user=self.users[0],
                            body=json.dumps(['other']), type='application/json')

        item = resp.json
        self.assertNotHasKeys(item['meta'], ['other'])

        # Error when deletion field names contain a period.
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='DELETE', user=self.users[0],
                            body=json.dumps(['foo', 'foo.bar']), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Invalid key foo.bar: keys must not contain the "." character.')

        # Error when deletion field names begin with a dollar-sign.
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='DELETE', user=self.users[0],
                            body=json.dumps(['foo', '$bar']), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Invalid key $bar: keys must not start with the "$" character.')

        # Make sure metadata cannot be added with invalid JSON
        metadata = {
            'test': 'allowed'
        }
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata).replace('"', "'"),
                            type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'],
                         'Invalid JSON passed in request body.')

        # Make sure metadata cannot be added if there is a period in the key
        # name
        metadata = {
            'foo.bar': 'notallowed'
        }
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Invalid key foo.bar: keys must not contain the "." character.')

        # Make sure metadata cannot be added if the key begins with a
        # dollar sign
        metadata = {
            '$foobar': 'alsonotallowed'
        }
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'],
            'Invalid key $foobar: keys must not start with the "$" character.')

        # Make sure metadata cannot be added with a blank key
        metadata = {
            '': 'stillnotallowed'
        }
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=self.users[0],
                            body=json.dumps(metadata), type='application/json')
        self.assertStatus(resp, 400)
        self.assertEqual(
            resp.json['message'], 'Key names must not be empty.')

    def testItemFiltering(self):
        """
        Test filtering private metadata from items.
        """
        # Create an item
        params = {
            'name': 'item with metadata',
            'description': ' a description ',
            'folderId': self.privateFolder['_id']
        }
        resp = self.request(path='/item', method='POST', params=params,
                            user=self.users[0])
        self.assertStatusOk(resp)

        # get the item object from the database
        item = Item().load(resp.json['_id'], force=True)

        # set a private property
        item['private'] = 'very secret metadata'
        item = Item().save(item)

        # get the item from the rest api
        resp = self.request(path='/item/%s' % str(item['_id']), method='GET',
                            user=self.users[0])
        self.assertStatusOk(resp)

        # assert that the private data is not included
        self.assertNotHasKeys(resp.json, ['private'])

    def testPathToRoot(self):
        firstChildName = 'firstChild'
        firstChildDesc = 'firstDesc'
        secondChildName = 'secondChild'
        secondChildDesc = 'secondDesc'

        firstChild = Folder().createFolder(
            self.publicFolder, firstChildName, firstChildDesc, creator=self.users[0])
        secondChild = Folder().createFolder(
            firstChild, secondChildName, secondChildDesc, creator=self.users[0])
        baseItem = Item().createItem('blah', self.users[0], secondChild, 'foo')

        resp = self.request(path='/item/%s/rootpath' % baseItem['_id'], method='GET')
        self.assertStatusOk(resp)
        pathToRoot = resp.json

        self.assertEqual(pathToRoot[0]['type'], 'user')
        self.assertEqual(pathToRoot[0]['object']['login'],
                         self.users[0]['login'])
        self.assertEqual(pathToRoot[1]['type'], 'folder')
        self.assertEqual(pathToRoot[1]['object']['name'],
                         self.publicFolder['name'])
        self.assertEqual(pathToRoot[2]['type'], 'folder')
        self.assertEqual(pathToRoot[2]['object']['name'], firstChild['name'])
        self.assertEqual(pathToRoot[3]['type'], 'folder')
        self.assertEqual(pathToRoot[3]['object']['name'], secondChild['name'])

    def testLazyFieldComputation(self):
        """
        Demonstrate that an item that is saved in the database without
        derived fields (like lowerName or baseParentId) get those values
        computed at load() time.
        """
        item = Item().createItem('My Item Name', creator=self.users[0], folder=self.publicFolder)

        self.assertEqual(item['lowerName'], 'my item name')
        self.assertEqual(item['baseParentId'], self.users[0]['_id'])

        # Force the item to be saved without lowerName and baseParentType fields
        del item['lowerName']
        del item['baseParentType']
        item = Item().save(item, validate=False)

        item = Item().find({'_id': item['_id']})[0]
        self.assertNotHasKeys(item, ('lowerName', 'baseParentType'))

        # Now ensure that calling load() actually populates those fields and
        # saves the results persistently
        Item().load(item['_id'], force=True)
        item = Item().find({'_id': item['_id']})[0]
        self.assertHasKeys(item, ('lowerName', 'baseParentType'))
        self.assertEqual(item['lowerName'], 'my item name')
        self.assertEqual(item['baseParentType'], 'user')
        self.assertEqual(item['baseParentId'], self.users[0]['_id'])
        # Also test that this works for a duplicate item, such that the
        # automatically renamed item still has the correct lowerName, and a
        # None description is changed to an empty string.
        item = Item().createItem(
            'My Item Name', creator=self.users[0], folder=self.publicFolder, description=None)
        # test if non-strings are coerced
        self.assertEqual(item['description'], '')
        item['description'] = 1
        item = Item().save(item)
        item = Item().findOne({'_id': item['_id']})
        self.assertEqual(item['description'], '1')
        # test if just missing lowerName is corrected.
        self.assertEqual(item['lowerName'], 'my item name (1)')
        del item['lowerName']
        item = Item().save(item, validate=False)
        item = Item().findOne({'_id': item['_id']})
        self.assertNotHasKeys(item, ('lowerName', ))
        Item().load(item['_id'], force=True)
        item = Item().findOne({'_id': item['_id']})
        self.assertHasKeys(item, ('lowerName', ))
        self.assertEqual(item['lowerName'], 'my item name (1)')

    def testParentsToRoot(self):
        """
        Demonstrate that forcing parentsToRoot will cause it to skip the
        filtering process.
        """
        item = Item().createItem('My Item Name', creator=self.users[0], folder=self.publicFolder)

        parents = Item().parentsToRoot(item, force=True)
        for parent in parents:
            self.assertNotIn('_accessLevel', parent['object'])

        parents = Item().parentsToRoot(item)
        for parent in parents:
            self.assertIn('_accessLevel', parent['object'])

    def testItemCopy(self):
        origItem = self._createItem(self.publicFolder['_id'],
                                    'test_for_copy', 'fake description',
                                    self.users[0])
        # Add metadata and files, since we want to make sure those get copied
        metadata = {
            'foo': 'value1',
            'test': 2
        }
        resp = self.request(
            path='/item/%s/metadata' % origItem['_id'], method='PUT', user=self.users[0],
            body=json.dumps(metadata), type='application/json')
        self.assertStatusOk(resp)
        self._testUploadFileToItem(origItem, 'file_1', self.users[0], 'foobar')
        self._testUploadFileToItem(origItem, 'file_2', self.users[0], 'foobz')
        # Also upload a link
        params = {
            'parentType': 'item',
            'parentId': origItem['_id'],
            'name': 'link_file',
            'linkUrl': 'http://www.google.com'
        }
        resp = self.request(path='/file', method='POST', user=self.users[0],
                            params=params)

        self.assertStatusOk(resp)
        # Copy to a new item.  It will be in the same folder, but we want a
        # different name.
        params = {
            'name': 'copied_item'
        }
        resp = self.request(path='/item/%s/copy' % origItem['_id'],
                            method='POST', user=self.users[0], params=params)
        self.assertStatusOk(resp)
        # Make sure size was returned correctly
        self.assertEqual(resp.json['size'], 11)
        # Now ask for the new item explicitly and check its metadata
        self.request(path='/item/%s' % resp.json['_id'],
                     user=self.users[0], type='application/json')
        self.assertStatusOk(resp)
        newItem = resp.json
        self.assertEqual(newItem['name'], 'copied_item')
        self.assertEqual(newItem['meta']['foo'], metadata['foo'])
        self.assertEqual(newItem['meta']['test'], metadata['test'])
        # Check if we can download the files from the new item
        resp = self.request(path='/item/%s/files' % newItem['_id'],
                            method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        newFiles = resp.json
        self.assertEqual(newFiles[0]['name'], 'file_1')
        self.assertEqual(newFiles[1]['name'], 'file_2')
        self.assertEqual(newFiles[2]['name'], 'link_file')
        self.assertEqual(newFiles[0]['size'], 6)
        self.assertEqual(newFiles[1]['size'], 5)
        self._testDownloadMultiFileItem(newItem, self.users[0],
                                        {'file_1': 'foobar', 'file_2': 'foobz',
                                         'link_file': 'http://www.google.com'})
        # Check to make sure the original item is still present
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params={'folderId': self.publicFolder['_id'],
                                    'text': 'test_for_copy'})
        self.assertStatusOk(resp)
        self.assertEqual(origItem['_id'], resp.json[0]['_id'])
        # Check to make sure the new item is still present
        resp = self.request(path='/item', method='GET', user=self.users[0],
                            params={'folderId': self.publicFolder['_id'],
                                    'text': 'copied_item'})
        self.assertStatusOk(resp)
        self.assertEqual(newItem['_id'], resp.json[0]['_id'])
        # Check that the provenance tag correctly points back
        # to the original item
        self.assertEqual(newItem['copyOfItem'], origItem['_id'])
        # Check if we can download the files from the old item and that they
        # are distinct from the files in the original item
        resp = self.request(path='/item/%s/files' % origItem['_id'],
                            method='GET', user=self.users[0])
        self.assertStatusOk(resp)
        origFiles = resp.json
        self._testDownloadMultiFileItem(origItem, self.users[0],
                                        {'file_1': 'foobar', 'file_2': 'foobz',
                                         'link_file': 'http://www.google.com'})
        for origFile, newFile in itertools.zip_longest(origFiles, newFiles):
            self.assertNotEqual(origFile['_id'], newFile['_id'])

    def testCookieAuth(self):
        """
        We make sure a cookie is sufficient for authentication for the item
        download endpoint. Also, while we're at it, we make sure it's not
        sufficient for other endpoints.
        """
        item = self._createItem(self.privateFolder['_id'],
                                'cookie_auth_download', '', self.users[0])
        self._testUploadFileToItem(item, 'file', self.users[0], 'foo')
        token = Token().createToken(self.users[0])
        cookie = 'girderToken=%s' % token['_id']

        # We should be able to download a private item using a cookie token
        resp = self.request(path='/item/%s/download' % item['_id'],
                            isJson=False, cookie=cookie)
        self.assertStatusOk(resp)
        self.assertEqual(self.getBody(resp), 'foo')

        # We should not be able to call GET /item/:id with a cookie token
        resp = self.request(path='/item/%s' % item['_id'], cookie=cookie)
        self.assertStatus(resp, 401)

        # Make sure the cookie has to be a valid token
        resp = self.request(path='/item/%s/download' % item['_id'],
                            cookie='girderToken=invalid_token')
        self.assertStatus(resp, 401)

    def testReuseExisting(self):
        item1 = Item().createItem('to be reused', creator=self.users[0], folder=self.publicFolder)

        item2 = Item().createItem('to be reused', creator=self.users[0], folder=self.publicFolder)

        item3 = Item().createItem(
            'to be reused', creator=self.users[0], folder=self.publicFolder, reuseExisting=True)

        self.assertNotEqual(item1['_id'], item2['_id'])
        self.assertEqual(item1['_id'], item3['_id'])
        self.assertEqual(item2['name'], 'to be reused (1)')
        self.assertEqual(item3['name'], 'to be reused')

    def testUpdateDuplicatedName(self):
        item1 = Item().createItem('foo', creator=self.users[0], folder=self.publicFolder)
        item2 = Item().createItem('bar', creator=self.users[0], folder=self.publicFolder)
        item2['name'] = 'foo'
        Item().save(item2, validate=False)
        self.assertEqual(item2['name'], 'foo')
        item1['size'] = 3
        Item().save(item1)
        self.assertEqual(item1['name'], 'foo')
