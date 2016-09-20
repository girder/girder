#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013, 2014 Kitware Inc.
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
import six

from tests import base
from girder import events
from girder.constants import AccessType
from server import constants


def setUpModule():
    base.enabledPlugins.append('provenance')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ProvenanceTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        # Create some test documents with an item
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
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

        # Track folder, item, and setting provenance initially
        self.model('setting').set(
            constants.PluginSettings.PROVENANCE_RESOURCES, 'folder,setting')

        coll1 = {
            'name': 'Test Collection',
            'description': 'test coll',
            'public': True,
            'creator': self.admin
        }
        self.coll1 = self.model('collection').createCollection(**coll1)

        folder1 = {
            'parent': self.coll1,
            'parentType': 'collection',
            'name': 'Public test folder',
            'creator': self.admin

        }
        self.folder1 = self.model('folder').createFolder(**folder1)
        self.model('folder').setUserAccess(
            self.folder1, self.user, level=AccessType.WRITE, save=False)
        self.model('folder').setPublic(self.folder1, True, save=True)

        item1 = {
            'name': 'Public object',
            'creator': self.admin,
            'folder': self.folder1
        }
        self.item1 = self.model('item').createItem(**item1)

    def _checkProvenance(self, resp, item, version, user, eventType,
                         matches=None, fileInfo=None, resource='item'):
        if resp is None:
            resp = self._getProvenance(item, user, resource=resource)
        self.assertStatusOk(resp)
        itemProvenance = resp.json
        self.assertEqual(itemProvenance['resourceId'], str(item['_id']))
        provenance = itemProvenance['provenance']
        self.assertEqual(provenance['eventType'], eventType)
        self.assertEqual(provenance['version'], version)
        self.assertEqual(str(provenance['eventUser']), str(user['_id']))
        if matches:
            for key in matches:
                self.assertEqual(provenance[key], matches[key])
        if fileInfo:
            for key in fileInfo:
                if isinstance(fileInfo[key], dict):
                    for subkey in fileInfo[key]:
                        self.assertEqual(provenance['file'][0][key][subkey],
                                         fileInfo[key][subkey])
                else:
                    self.assertEqual(provenance['file'][0][key], fileInfo[key])

    def _getProvenance(self, item, user, version=None, resource='item',
                       checkOk=True):
        params = {}
        if version is not None:
            params = {'version': version}
        resp = self.request(
            path='/%s/%s/provenance' % (resource, item['_id']),
            method='GET', user=user, type='application/json', params=params)
        if checkOk:
            self.assertStatusOk(resp)
        return resp

    def _getProvenanceAfterMetadata(self, item, meta, user):
        resp = self.request(path='/item/%s/metadata' % item['_id'],
                            method='PUT', user=user, body=json.dumps(meta),
                            type='application/json')
        self.assertStatusOk(resp)
        return self._getProvenance(item, user)

    def testProvenanceItemMetadata(self):
        """
        Test item provenance endpoint with metadata and basic changes
        """
        item = self.item1
        user = self.user
        admin = self.admin

        # check that the first version of the item exists
        # ensure version 1, created by admin user, with creation event
        self._checkProvenance(None, item, 1, admin, 'creation')

        # update meta to {x:y}
        metadata1 = {'x': 'y'}
        resp = self._getProvenanceAfterMetadata(item, metadata1, admin)
        # ensure version 2, updated by admin user, with update event, and meta
        # in provenance matches
        self._checkProvenance(resp, item, 2, admin, 'update',
                              {'new': {'meta': metadata1}})

        # update meta to {} by regular user, we have to send in the key to
        # remove it but check the saved metadata against {}
        metadata2 = {'x': None}
        resp = self._getProvenanceAfterMetadata(item, metadata2, user)
        # ensure version 3, updated by regular user, with update event, and
        # meta in provenance matches
        self._checkProvenance(resp, item, 3, user, 'update',
                              {'old': {'meta': metadata1},
                               'new': {'meta': {}}})

        # update meta to {x:y} by regular user
        metadata3 = {'x': 'y'}
        resp = self._getProvenanceAfterMetadata(item, metadata3, user)
        # ensure version 4, updated by regular user, with update event, and
        # meta in provenance matches
        self._checkProvenance(resp, item, 4, user, 'update',
                              {'old': {'meta': {}},
                               'new': {'meta': metadata3}})

        # update meta to {x:z} by regular user
        metadata4 = {'x': 'z'}
        resp = self._getProvenanceAfterMetadata(item, metadata4, user)
        # ensure version 5, updated by regular user, with update event, and
        # meta in provenance matches
        self._checkProvenance(resp, item, 5, user, 'update',
                              {'old': {'meta': metadata3},
                               'new': {'meta': metadata4}})

        # update meta to {x:z, q:u} by regular user
        metadata5 = {'x': 'z', 'q': 'u'}
        resp = self._getProvenanceAfterMetadata(item, metadata5, user)
        # ensure version 6, updated by regular user, with update event, and
        # meta in provenance matches
        self._checkProvenance(resp, item, 6, user, 'update',
                              {'old': {'meta': metadata4},
                               'new': {'meta': metadata5}})

        # update meta to {q:a} by regular user
        metadata6 = {'x': None, 'q': 'a'}
        resp = self._getProvenanceAfterMetadata(item, metadata6, user)
        # ensure version 7, updated by regular user, with update event, and
        # meta in provenance matches
        self._checkProvenance(resp, item, 7, user, 'update',
                              {'old': {'meta': metadata5},
                               'new': {'meta': {'q': 'a'}}})

        # Change the item name and description
        params = {'name': 'Renamed object', 'description': 'New description'}
        resp = self.request(path='/item/%s' % item['_id'], method='PUT',
                            user=admin, params=params)
        self.assertStatusOk(resp)
        params['lowerName'] = params['name'].lower()
        self._checkProvenance(None, item, 8, admin, 'update', {'new': params})

        # Copy the item and check that we marked it as copied
        params = {'name': 'Copied object'}
        resp = self.request(path='/item/%s/copy' % item['_id'],
                            method='POST', user=admin, params=params)
        self.assertStatusOk(resp)
        newItem = resp.json
        self._checkProvenance(None, newItem, 9, admin, 'copy',
                              {'originalId': str(item['_id'])})

    def testProvenanceItemFiles(self):
        """
        Test item provenance when adding, modifying, and deleting files.
        """
        item = self.item1
        admin = self.admin

        # Test adding a new file to an existing item
        fileData1 = 'Hello world'
        fileData2 = 'Hello world, again'
        fileName1 = 'helloWorld.txt'
        fileName2 = 'helloWorldEdit.txt'
        resp = self.request(
            path='/file', method='POST', user=admin, params={
                'parentType': 'item',
                'parentId': item['_id'],
                'name': fileName1,
                'size': len(fileData1),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', fileName1, fileData1)]
        resp = self.multipartRequest(
            path='/file/chunk', user=admin, fields=fields, files=files)
        self.assertStatusOk(resp)
        file1 = resp.json
        self._checkProvenance(None, item, 2, admin, 'fileAdded',
                              fileInfo={'fileId': str(file1['_id']),
                                        'new': {'mimeType': 'text/plain',
                                                'size': len(fileData1),
                                                'name': fileName1}})
        # Edit the file name
        resp = self.request(path='/file/%s' % file1['_id'], method='PUT',
                            user=admin, params={'name': fileName2})
        self.assertStatusOk(resp)
        self._checkProvenance(None, item, 3, admin, 'fileUpdate',
                              fileInfo={'fileId': str(file1['_id']),
                                        'old': {'name': fileName1},
                                        'new': {'name': fileName2}})
        # Reupload the file
        resp = self.request(path='/file/%s/contents' % file1['_id'],
                            method='PUT', user=admin,
                            params={'size': len(fileData2)})
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']
        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', fileName1, fileData2)]
        resp = self.multipartRequest(
            path='/file/chunk', user=admin, fields=fields, files=files)
        self.assertStatusOk(resp)
        self.assertEqual(file1['_id'], resp.json['_id'])
        self._checkProvenance(None, item, 4, admin, 'fileUpdate',
                              fileInfo={'fileId': str(file1['_id']),
                                        'old': {'size': len(fileData1)},
                                        'new': {'size': len(fileData2)}})
        # Delete the file
        resp = self.request(path='/file/%s' % file1['_id'],
                            method='DELETE', user=admin)
        self.assertStatusOk(resp)
        self._checkProvenance(None, item, 5, admin, 'fileRemoved',
                              fileInfo={'fileId': str(file1['_id']),
                                        'old': {'size': len(fileData2),
                                                'name': fileName2}})

    def testProvenanceFolder(self):
        """
        Test folder provenance, including turning off and on the provenance
        handling of folders.
        """
        folder1 = self.folder1
        user = self.admin

        # check that the first version of the folder provenance exists
        self._checkProvenance(None, folder1, 1, user, 'creation',
                              resource='folder')
        # Edit the folder and check again
        params1 = {'name': 'Renamed folder', 'description': 'New description'}
        resp = self.request(path='/folder/%s' % folder1['_id'],
                            method='PUT', user=user, params=params1)
        self.assertStatusOk(resp)
        params1['lowerName'] = params1['name'].lower()
        self._checkProvenance(None, folder1, 2, user, 'update',
                              {'new': params1}, resource='folder')

        # Turn off folder provenance and make sure asking for it fails
        self.model('setting').set(
            constants.PluginSettings.PROVENANCE_RESOURCES, 'setting')
        resp = self._getProvenance(folder1, user, resource='folder',
                                   checkOk=False)
        self.assertStatus(resp, 400)
        # While folder provenance is off, create a second folder and edit the
        # first folder
        params2 = {'name': 'Renamed Again', 'description': 'Description 2'}
        resp = self.request(path='/folder/%s' % folder1['_id'],
                            method='PUT', user=user, params=params2)
        self.assertStatusOk(resp)
        params2['lowerName'] = params2['name'].lower()

        folder2 = {
            'parent': self.coll1,
            'parentType': 'collection',
            'name': 'Private test folder',
            'creator': self.admin
        }
        folder2 = self.model('folder').createFolder(**folder2)
        # Turn back on folder provenance and check that it didn't record the
        # changes we made.
        self.model('setting').set(
            constants.PluginSettings.PROVENANCE_RESOURCES, 'folder,setting')
        self._checkProvenance(None, folder1, 2, user, 'update',
                              {'new': params1}, resource='folder')
        # Changing folder1 again should now show this change, and the old value
        # should show the gap in the data
        params3 = {'name': 'Renamed C', 'description': 'Description 3'}
        resp = self.request(path='/folder/%s' % folder1['_id'],
                            method='PUT', user=user, params=params3)
        self.assertStatusOk(resp)
        params3['lowerName'] = params3['name'].lower()
        self._checkProvenance(None, folder1, 3, user, 'update',
                              {'old': params2, 'new': params3},
                              resource='folder')
        # The new folder should have no provenance
        resp = self._getProvenance(folder2, user, resource='folder')
        self.assertEqual(resp.json['resourceId'], str(folder2['_id']))
        self.assertIsNone(resp.json['provenance'])
        # Edit the new folder; it should show the unknown history followed by
        # the edit
        params4 = {'description': 'Folder 2 Description'}
        resp = self.request(path='/folder/%s' % folder2['_id'],
                            method='PUT', user=user, params=params4)
        self.assertStatusOk(resp)
        resp = self._getProvenance(folder2, user, 1, resource='folder')
        self._checkProvenance(resp, folder2, 1, user, 'unknownHistory',
                              resource='folder')
        self._checkProvenance(None, folder2, 2, user, 'update',
                              {'new': params4}, resource='folder')
        # We should also see the initial history using negative indexing
        resp = self._getProvenance(folder2, user, -2, resource='folder')
        self._checkProvenance(resp, folder2, 1, user, 'unknownHistory',
                              resource='folder')
        # We should be able to get the entire history using 'all'
        resp = self._getProvenance(folder2, user, 'all', resource='folder')
        self.assertEqual(resp.json['resourceId'], str(folder2['_id']))
        self.assertEqual(len(resp.json['provenance']), 2)
        self.assertEqual(resp.json['provenance'][0]['eventType'],
                         'unknownHistory')
        self.assertEqual(resp.json['provenance'][1]['eventType'], 'update')
        # We should get an error if we ask for a nonsense version
        resp = self._getProvenance(folder2, user, 'not_a_version',
                                   resource='folder', checkOk=False)
        self.assertStatus(resp, 400)

    def testProvenanceSetting(self):
        # After trying to set this set, only some of them should have events
        self.model('setting').set(
            constants.PluginSettings.PROVENANCE_RESOURCES,
            'file,notification,unknown')
        checkList = {
            'item': True,
            'file': True,
            'notification': False,
            'unknown': True}
        for key in checkList:
            eventName = 'model.%s.save' % key
            self.assertTrue((eventName in events._mapping and 'provenance' in
                            [h['name'] for h in events._mapping[eventName]])
                            is checkList[key])
        # Setting a blank should be okay.  It should also remove all but item
        # event mappings
        self.model('setting').set(
            constants.PluginSettings.PROVENANCE_RESOURCES, '')
        for key in checkList:
            eventName = 'model.%s.save' % key
            self.assertTrue((eventName in events._mapping and 'provenance' in
                            [h['name'] for h in events._mapping[eventName]])
                            is (key == 'item'))

    def testProvenanceFileWithoutItem(self):
        fileData = b'this is a test'
        file = self.model('upload').uploadFromFile(
            obj=six.BytesIO(fileData), size=len(fileData), name='test',
            parentType=None, parent=None, user=self.admin)
        self.assertIsNone(file.get('itemId'))
        file['name'] = 'test2'
        file = self.model('file').save(file)
        self.model('file').remove(file)
