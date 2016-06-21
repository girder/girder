#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

import datetime
import io
import json
import os
import six
import zipfile

from .. import base

import girder.utility.ziputil
from girder.models.notification import ProgressState
from six.moves import range, urllib


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class ResourceTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }
        self.admin = self.model('user').createUser(**admin)
        user = {
            'email': 'user@email.com',
            'login': 'userlogin',
            'firstName': 'Normal',
            'lastName': 'User',
            'password': 'goodpassword'
        }
        self.user = self.model('user').createUser(**user)

    def _createFiles(self, user=None):
        """
        Create a set of items, folders, files, metadata, and collections for
        testing.

        :param user: the user who should own these items.
        """
        if user is None:
            user = self.admin
        self.expectedZip = {}
        # Create a collection
        coll = {
            'name': 'Test Collection',
            'description': 'The description',
            'public': True,
            'creator': user
        }
        self.collection = self.model('collection').createCollection(**coll)
        self.collectionPrivateFolder = self.model('folder').createFolder(
            parent=self.collection, parentType='collection', name='Private',
            creator=user, public=False)

        # Get the admin user's folders
        resp = self.request(
            path='/folder', method='GET', user=user, params={
                'parentType': 'user',
                'parentId': user['_id'],
                'sort': 'name',
                'sortdir': 1
            })
        self.adminPrivateFolder = self.model('folder').load(
            resp.json[0]['_id'], user=user)
        self.adminPublicFolder = self.model('folder').load(
            resp.json[1]['_id'], user=user)
        # Create a folder within the admin public forlder
        resp = self.request(
            path='/folder', method='POST', user=user, params={
                'name': 'Folder 1', 'parentId': self.adminPublicFolder['_id']
            })
        self.adminSubFolder = resp.json
        # Create a series of items
        self.items = []
        self.items.append(self.model('item').createItem(
            'Item 1', self.admin, self.adminPublicFolder))
        self.items.append(self.model('item').createItem(
            'Item 2', self.admin, self.adminPublicFolder))
        self.items.append(self.model('item').createItem(
            'Item 3', self.admin, self.adminSubFolder))
        self.items.append(self.model('item').createItem(
            'Item 4', self.admin, self.collectionPrivateFolder))
        self.items.append(self.model('item').createItem(
            'Item 5', self.admin, self.collectionPrivateFolder))
        # Upload a series of files
        file, path, contents = self._uploadFile('File 1', self.items[0])
        self.file1 = file
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 2', self.items[0])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 3', self.items[1])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 4', self.items[2])
        self.expectedZip[path] = contents
        file, path, contents = self._uploadFile('File 5', self.items[3])
        self.expectedZip[path] = contents
        # place some metadata on two of the items and one of the folders
        meta = {'key': 'value'}
        self.model('item').setMetadata(self.items[2], meta)
        parents = self.model('item').parentsToRoot(self.items[2], self.admin)
        path = os.path.join(*([part['object'].get(
            'name', part['object'].get('login', '')) for part in parents] +
            [self.items[2]['name'], 'girder-item-metadata.json']))
        self.expectedZip[path] = meta

        meta = {'x': 'y'}
        self.model('item').setMetadata(self.items[4], meta)
        parents = self.model('item').parentsToRoot(self.items[4], self.admin)
        path = os.path.join(*([part['object'].get(
            'name', part['object'].get('login', '')) for part in parents] +
            [self.items[4]['name'], 'girder-item-metadata.json']))
        self.expectedZip[path] = meta

        meta = {'key2': 'value2', 'date': datetime.datetime.utcnow()}
        # mongo rounds to millisecond, so adjust our expectations
        meta['date'] -= datetime.timedelta(
            microseconds=meta['date'].microsecond % 1000)
        self.model('folder').setMetadata(self.adminPublicFolder, meta)
        parents = self.model('folder').parentsToRoot(self.adminPublicFolder,
                                                     user=user)
        path = os.path.join(*([part['object'].get(
            'name', part['object'].get('login', '')) for part in parents] +
            [self.adminPublicFolder['name'], 'girder-folder-metadata.json']))
        self.expectedZip[path] = meta

    def _uploadFile(self, name, item):
        """
        Upload a random file to an item.
        :param name: name of the file.
        :param item: item to upload the file to.
        :returns: file: the created file object
                  path: the path to the file within the parent hierarchy.
                  contents: the contents that were generated for the file.
        """
        contents = os.urandom(1024)
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'item',
                'parentId': item['_id'],
                'name': name,
                'size': len(contents),
                'mimeType': 'application/octet-stream'
            })
        self.assertStatusOk(resp)
        upload = resp.json
        fields = [('offset', 0), ('uploadId', upload['_id'])]
        files = [('chunk', name, contents)]
        resp = self.multipartRequest(
            path='/file/chunk', user=self.admin, fields=fields, files=files)
        self.assertStatusOk(resp)
        file = resp.json
        parents = self.model('item').parentsToRoot(item, user=self.admin)
        path = os.path.join(*([part['object'].get(
            'name', part['object'].get('login', '')) for part in parents] +
            [item['name'], name]))
        return (file, path, contents)

    def testDownloadResources(self):
        self._createFiles()
        resourceList = {
            'collection': [str(self.collection['_id'])],
            'user': [str(self.admin['_id'])]
            }
        # We should fail with bad json, an empty list, an invalid item in the
        # list, or a list that is an odd format.
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': 'this_is_not_json',
            }, isJson=False)
        self.assertStatus(resp, 400)
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps('this_is_not_a_dict_of_resources')
            }, isJson=False)
        self.assertStatus(resp, 400)
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps({'not_a_resource': ['not_an_id']})
            }, isJson=False)
        self.assertStatus(resp, 400)
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps({'item': []})
            }, isJson=False)
        self.assertStatus(resp, 400)
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps({'item': [str(self.admin['_id'])]})
            }, isJson=False)
        self.assertStatus(resp, 400)
        # Download the resources
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps(resourceList),
                'includeMetadata': True
            }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)
        self.assertHasKeys(self.expectedZip, zip.namelist())
        self.assertHasKeys(zip.namelist(), self.expectedZip)
        for name in zip.namelist():
            expected = self.expectedZip[name]
            if isinstance(expected, dict):
                self.assertEqual(json.loads(zip.read(name).decode('utf8')),
                                 json.loads(json.dumps(expected, default=str)))
            else:
                if not isinstance(expected, six.binary_type):
                    expected = expected.encode('utf8')
                self.assertEqual(expected, zip.read(name))
        # Download the same resources again, this time triggering the large zip
        # file creation (artifically forced).  We could do this naturally by
        # downloading >65536 files, but that would make the test take several
        # minutes.
        girder.utility.ziputil.Z_FILECOUNT_LIMIT = 5
        resourceList = {
            'item': [str(item['_id']) for item in self.items]
            }
        resp = self.request(
            path='/resource/download', method='POST', user=self.admin, params={
                'resources': json.dumps(resourceList),
                'includeMetadata': True
            }, isJson=False,
            additionalHeaders=[('X-HTTP-Method-Override', 'GET')])
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)

        # Test deleting resources
        resourceList = {
            'collection': [str(self.collection['_id'])],
            'folder': [str(self.adminSubFolder['_id'])],
            }
        resp = self.request(
            path='/resource', method='DELETE', user=self.admin, params={
                'resources': json.dumps(resourceList),
                'progress': True
            }, isJson=False)
        self.assertStatusOk(resp)
        # Make sure progress record exists and that it is set to expire soon
        notifs = list(self.model('notification').get(self.admin))
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]['type'], 'progress')
        self.assertEqual(notifs[0]['data']['state'], ProgressState.SUCCESS)
        self.assertEqual(notifs[0]['data']['title'], 'Deleting resources')
        self.assertEqual(notifs[0]['data']['message'], 'Done')
        self.assertEqual(notifs[0]['data']['total'], 6)
        self.assertEqual(notifs[0]['data']['current'], 6)
        self.assertTrue(notifs[0]['expires'] < datetime.datetime.utcnow() +
                        datetime.timedelta(minutes=1))
        # Test deletes using a body on the request
        resourceList = {
            'item': [str(self.items[1]['_id'])]
            }
        resp = self.request(
            path='/resource', method='DELETE', user=self.admin,
            body=urllib.parse.urlencode({
                'resources': json.dumps(resourceList)
            }),
            type='application/x-www-form-urlencoded', isJson=False)
        self.assertStatusOk(resp)
        # Test deletes using POST and override method
        resourceList = {
            'item': [str(self.items[0]['_id'])]
            }
        resp = self.request(
            path='/resource', method='POST', user=self.admin, params={
                'resources': json.dumps(resourceList)
            }, isJson=False,
            additionalHeaders=[('X-HTTP-Method-Override', 'DELETE')])
        self.assertStatusOk(resp)
        # All of the items should be gone now
        resp = self.request(path='/item', method='GET', user=self.admin,
                            params={'text': 'Item'})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)

        # Add a file under the admin private folder
        item = self.model('item').createItem(
            'Private Item', self.admin, self.adminPrivateFolder)
        _, path, contents = self._uploadFile('private_file', item)
        self.assertEqual(path, 'goodlogin/Private/Private Item/private_file')

        # Download as admin, should get private file
        resp = self.request(
            path='/resource/download', method='GET', user=self.admin, params={
                'resources': json.dumps({'user': [str(self.admin['_id'])]})
            }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)
        self.assertEqual(zip.namelist(), [path])
        self.assertEqual(zip.read(path), contents)

        # Download as normal user, should get empty zip
        resp = self.request(
            path='/resource/download', method='GET', user=self.user, params={
                'resources': json.dumps({'user': [str(self.admin['_id'])]})
            }, isJson=False)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Content-Type'], 'application/zip')
        zip = zipfile.ZipFile(io.BytesIO(self.getBody(resp, text=False)), 'r')
        self.assertTrue(zip.testzip() is None)
        self.assertEqual(zip.namelist(), [])

    def testDeleteResources(self):
        # Some of the deletes were tested with the downloads.
        self._createFiles(user=self.user)
        # Test delete of a file
        resp = self.request(
            path='/resource', method='DELETE', user=self.admin, params={
                'resources': json.dumps({'file': [str(self.file1['_id'])]}),
                'progress': True
            }, isJson=False)
        self.assertStatusOk(resp)
        # Test delete of a user who owns a folder
        resp = self.request(
            path='/resource', method='DELETE', user=self.admin, params={
                'resources': json.dumps({'user': [str(self.user['_id'])]}),
                'progress': True
            }, isJson=False)
        self.assertStatusOk(resp)
        resp = self.request(path='/user', method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        # Deleting a non-existant object should give an error
        resp = self.request(
            path='/resource', method='DELETE', user=self.admin, params={
                'resources': json.dumps({'item': [str(self.admin['_id'])]})
            }, isJson=False)
        self.assertStatus(resp, 400)

    def testGetResourceById(self):
        self._createFiles()
        resp = self.request(path='/resource/%s' % self.admin['_id'],
                            method='GET', user=self.admin,
                            params={'type': 'user'})
        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']), str(self.admin['_id']))
        self.assertEqual(resp.json['email'], 'good@email.com')
        # Get a file via this method
        resp = self.request(path='/resource/%s' % self.file1['_id'],
                            method='GET', user=self.admin,
                            params={'type': 'file'})
        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']), str(self.file1['_id']))

    def testGetResourceByPath(self):
        self._createFiles()

        # test users
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.admin,
                            params={'path': '/user/goodlogin'})

        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']), str(self.admin['_id']))

        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/user/userlogin'})
        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']), str(self.user['_id']))

        # test collections
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/collection/Test Collection'})
        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']), str(self.collection['_id']))

        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.admin,
                            params={'path':
                                    '/collection/Test Collection/' +
                                    self.collectionPrivateFolder['name']})
        self.assertStatusOk(resp)
        self.assertEqual(str(resp.json['_id']),
                         str(self.collectionPrivateFolder['_id']))

        # test folders
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/user/goodlogin/Public'})
        self.assertStatusOk(resp)
        self.assertEqual(
            str(resp.json['_id']), str(self.adminPublicFolder['_id']))

        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/user/goodlogin/Private'})
        self.assertStatus(resp, 403)

        # test subfolders
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.admin,
                            params={'path': '/user/goodlogin/Public/Folder 1'})
        self.assertStatusOk(resp)
        self.assertEqual(
            str(resp.json['_id']), str(self.adminSubFolder['_id']))

        # test items
        privateFolder = self.collectionPrivateFolder['name']
        paths = ('/user/goodlogin/Public/Item 1',
                 '/user/goodlogin/Public/Item 2',
                 '/user/goodlogin/Public/Folder 1/Item 3',
                 '/collection/Test Collection/%s/Item 4' % privateFolder,
                 '/collection/Test Collection/%s/Item 5' % privateFolder)

        users = (self.user,
                 self.user,
                 self.user,
                 self.admin,
                 self.admin)

        for path, item, user in zip(paths, self.items, users):
            resp = self.request(path='/resource/lookup',
                                method='GET', user=user,
                                params={'path': path})

            self.assertStatusOk(resp)
            self.assertEqual(
                str(resp.json['_id']), str(item['_id']))

        # test bogus path
        # test is not set
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/bogus/path'})
        self.assertStatus(resp, 400)
        # test is set to false, response code should be 400
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/bogus/path',
                                    'test': False})
        self.assertStatus(resp, 400)

        # test is set to true, response code should be 200 and response body
        # should be null (None)
        resp = self.request(path='/resource/lookup',
                            method='GET', user=self.user,
                            params={'path': '/bogus/path',
                                    'test': True})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

    def testMove(self):
        self._createFiles()
        # Move item1 from the public to the private folder
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({'item': [str(self.items[0]['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminPrivateFolder['_id']),
                'progress': True
            })
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s' % self.items[0]['_id'],
                            method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['folderId'],
                         str(self.adminPrivateFolder['_id']))
        # We shouldn't be able to move the item into the user
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({'item': [str(self.items[0]['_id'])]}),
                'parentType': 'user',
                'parentId': str(self.admin['_id'])
            })
        self.assertStatus(resp, 400)
        # Asking to move into a file is also an error
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({'item': [str(self.items[0]['_id'])]}),
                'parentType': 'file',
                'parentId': str(self.file1['_id'])
            })
        self.assertStatus(resp, 400)
        # Move item1 and subFolder from the public to the private folder (item1
        # is already there).
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({
                    'folder': [str(self.adminSubFolder['_id'])],
                    'item': [str(self.items[0]['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminPrivateFolder['_id']),
                'progress': True
            })
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s' % self.items[0]['_id'],
                            method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['folderId'],
                         str(self.adminPrivateFolder['_id']))
        resp = self.request(
            path='/folder/%s' % self.adminSubFolder['_id'], method='GET',
            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentId'],
                         str(self.adminPrivateFolder['_id']))
        # You can't move a folder into itself
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({
                    'folder': [str(self.adminSubFolder['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminSubFolder['_id']),
                'progress': True
            })
        self.assertStatus(resp, 400)
        # You can move a folder into a user
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({
                    'folder': [str(self.adminSubFolder['_id'])]}),
                'parentType': 'user',
                'parentId': str(self.admin['_id'])
            })
        self.assertStatusOk(resp)
        resp = self.request(
            path='/folder/%s' % self.adminSubFolder['_id'], method='GET',
            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['parentCollection'], 'user')
        self.assertEqual(resp.json['parentId'], str(self.admin['_id']))
        # The non-admin user can't move other people's stuff
        resp = self.request(
            path='/resource/move', method='PUT', user=self.user,
            params={
                'resources': json.dumps({'item': [str(self.items[2]['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminPublicFolder['_id'])
            })
        self.assertStatus(resp, 403)
        # You can't move files
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin,
            params={
                'resources': json.dumps({
                    'file': [str(self.file1['_id'])]}),
                'parentType': 'item',
                'parentId': str(self.items[1]['_id'])
            })
        self.assertStatus(resp, 400)
        # Moving a non-existant object should give an error
        resp = self.request(
            path='/resource/move', method='PUT', user=self.admin, params={
                'resources': json.dumps({'item': [str(self.admin['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminPublicFolder['_id'])
            }, isJson=False)
        self.assertStatus(resp, 400)

    def testCopy(self):
        self._createFiles()
        # The non-admin user should be able to copy public documents
        resp = self.request(
            path='/resource/copy', method='POST', user=self.user,
            params={
                'resources': json.dumps({
                    'folder': [str(self.adminSubFolder['_id'])]}),
                'parentType': 'user',
                'parentId': str(self.user['_id']),
                'progress': True
            })
        self.assertStatusOk(resp)
        resp = self.request(
            path='/folder', method='GET', user=self.user,
            params={
                'parentType': 'user',
                'parentId': str(self.user['_id']),
                'text': 'Folder 1'})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        copiedFolder = resp.json[0]
        self.assertNotEqual(str(copiedFolder['_id']),
                            str(self.adminSubFolder['_id']))
        # We should have reported 2 things copied in the progress (1 folder and
        # 1 item)
        resp = self.request(
            path='/notification/stream', method='GET', user=self.user,
            isJson=False, params={'timeout': 1})
        messages = self.getSseMessages(resp)
        self.assertTrue(len(messages) >= 1)
        self.assertEqual(messages[-1]['data']['current'], 2)
        # The non-admin user should not be able to copy private documents
        resp = self.request(
            path='/resource/copy', method='POST', user=self.user,
            params={
                'resources': json.dumps({
                    'folder': [str(self.adminPrivateFolder['_id'])]}),
                'parentType': 'user',
                'parentId': str(self.user['_id'])
            })
        self.assertStatus(resp, 403)
        # Copy a group of items from different spots.  Do this as admin
        resp = self.request(
            path='/resource/copy', method='POST', user=self.admin,
            params={
                'resources': json.dumps({
                    'item': [str(item['_id']) for item in self.items]}),
                'parentType': 'folder',
                'parentId': str(copiedFolder['_id']),
                'progress': True
            })
        self.assertStatusOk(resp)
        # We already had one item in that folder, so now we should have one
        # more than in the self.items list.  The user should be able to see
        # these items.
        resp = self.request(path='/item', method='GET', user=self.user,
                            params={'folderId': str(copiedFolder['_id'])})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), len(self.items)+1)
        # Copying a non-existant object should give an error
        resp = self.request(
            path='/resource/copy', method='POST', user=self.admin, params={
                'resources': json.dumps({'item': [str(self.admin['_id'])]}),
                'parentType': 'folder',
                'parentId': str(self.adminPublicFolder['_id'])
            }, isJson=False)
        self.assertStatus(resp, 400)

    def testZipUtil(self):
        # Exercise the large zip file code

        def genEmptyFile(fileLength, chunkSize=65536):
            chunk = '\0' * chunkSize

            def genEmptyData():
                for val in range(0, fileLength, chunkSize):
                    if fileLength - val < chunkSize:
                        yield chunk[:fileLength - val]
                    else:
                        yield chunk

            return genEmptyData

        zip = girder.utility.ziputil.ZipGenerator()
        # Most of the time in generating a zip file is spent in CRC
        # calculation.  We turn it off so that we can perform tests in a timely
        # fashion.
        zip.useCRC = False
        for data in zip.addFile(
                genEmptyFile(6 * 1024 * 1024 * 1024), 'bigfile'):
            pass
        # Add a second small file at the end to test some of the other Zip64
        # code
        for data in zip.addFile(genEmptyFile(100), 'smallfile'):
            pass
        # Test that we don't crash on Unicode file names
        for data in zip.addFile(
                genEmptyFile(100), u'\u0421\u0443\u043f\u0435\u0440-\u0440'
                '\u0443\u0441\u0441\u043a\u0438, \u0627\u0633\u0645 \u0627'
                '\u0644\u0645\u0644\u0641 \u0628\u0627\u0644\u0644\u063a'
                '\u0629 \u0627\u0644\u0639\u0631\u0628\u064a\u0629'):
            pass
        # Test filename with a null
        for data in zip.addFile(genEmptyFile(100), 'with\x00null'):
            pass
        footer = zip.footer()
        self.assertEqual(footer[-6:], b'\xFF\xFF\xFF\xFF\x00\x00')
