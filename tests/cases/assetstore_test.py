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

import os

from .. import base
from girder.constants import AccessType, AssetstoreType, ROOT_DIR


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class AssetstoreTestCase(base.TestCase):

    def setUp(self):
        base.TestCase.setUp(self)

        info = {
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**info)

    def testCreateAndSetCurrent(self):
        # Non admin users should not be able to see assetstore list
        resp = self.request(path='/assetstore', method='GET')
        self.assertStatus(resp, 401)

        resp = self.request(path='/assetstore', method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(1, len(resp.json))
        oldAssetstore = resp.json[0]

        self.assertTrue(oldAssetstore['current'])
        self.assertEqual(oldAssetstore['name'], 'Test')
        self.assertEqual(oldAssetstore['type'], AssetstoreType.FILESYSTEM)

        params = {
            'name': 'Test',
            'type': AssetstoreType.GRIDFS
        }

        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertMissingParameter(resp, 'db')

        params['type'] = AssetstoreType.FILESYSTEM

        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertMissingParameter(resp, 'root')

        params['root'] = os.path.join(oldAssetstore['root'], 'other')
        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['field'], 'name')

        params['name'] = 'New Name'
        # Actually creates the new assetstore
        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertStatusOk(resp)
        assetstore = resp.json
        self.assertEqual(assetstore['name'], 'New Name')
        self.assertFalse(assetstore['current'])

        # Set the new assetstore as current
        params = {
            'name': assetstore['name'],
            'root': assetstore['root'],
            'current': True
        }
        resp = self.request(path='/assetstore/{}'.format(assetstore['_id']),
                            method='PUT', user=self.admin, params=params)
        self.assertStatusOk(resp)
        assetstore = self.model('assetstore').load(resp.json['_id'])
        self.assertTrue(assetstore['current'])

        # The old assetstore should no longer be current
        oldAssetstore = self.model('assetstore').load(oldAssetstore['_id'])
        self.assertFalse(oldAssetstore['current'])

    def testDeleteAssetstore(self):
        resp = self.request(path='/assetstore', method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(1, len(resp.json))
        assetstore = self.model('assetstore').load(resp.json[0]['_id'])

        # Anonymous user should not be able to delete assestores
        resp = self.request(path='/assetstore/{}'.format(assetstore['_id']),
                            method='DELETE')
        self.assertStatus(resp, 401)

        # Simulate the existence of a file within the assetstore
        folders = self.model('folder').childFolders(
            self.admin, 'user', user=self.admin)
        item = self.model('item').createItem(
            name='x.txt', creator=self.admin, folder=folders.next())
        file = self.model('file').createFile(
            creator=self.admin, item=item, name='x.txt',
            size=1, assetstore=assetstore, mimeType='text/plain')
        file['sha512'] = 'x'  # add this dummy value to simulate real file

        resp = self.request(path='/assetstore/{}'.format(assetstore['_id']),
                            method='DELETE', user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You may not delete an '
                         'assetstore that contains files.')

        # Delete the offending file, we can now delete the assetstore
        self.model('file').remove(file)
        resp = self.request(path='/assetstore/{}'.format(assetstore['_id']),
                            method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['message'],
                         'Deleted assetstore {}.'.format(assetstore['name']))

        resp = self.request(path='/assetstore', method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(0, len(resp.json))

    def testS3AssetstoreAdapter(self):
        # Delete the default assetstore
        self.model('assetstore').remove(self.assetstore)

        params = {
            'name': 'S3 Assetstore',
            'type': AssetstoreType.S3,
            'bucket': 'bucketname',
            'accessKeyId': 'someKey',
            'secretKey': 'someSecret',
            'prefix': 'foo/bar',
            'current': True
        }

        # Validation should fail with bad credentials
        resp = self.request(path='/assetstore', method='POST', user=self.admin,
                            params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json, {
            'type': 'validation',
            'field': 'bucket',
            'message': 'Unable to write into bucket "bucketname".'
        })

        # Force save of the assetstore since we can't validate it in test mode
        params['secret'] = params['secretKey']
        del params['secretKey']
        assetstore = self.model('assetstore').save(params, validate=False)

        # Test init for a single-chunk upload
        folders = self.model('folder').childFolders(
            self.admin, 'user', user=self.admin)
        params = {
            'parentType': 'folder',
            'parentId': folders.next()['_id'],
            'name': 'My File.txt',
            'size': 1024,
            'mimeType': 'text/plain'
        }
        resp = self.request(path='/file', method='POST', user=self.admin,
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['received'], 0)
        self.assertEqual(resp.json['size'], 1024)
        self.assertEqual(resp.json['behavior'], 's3')

        s3Info = resp.json['s3']
        self.assertEqual(s3Info['chunked'], False)
        self.assertEqual(type(s3Info['chunkLength']), int)
        self.assertEqual(s3Info['request']['method'], 'PUT')
        self.assertTrue(s3Info['request']['url'].startswith(
                        'https://bucketname.s3.amazonaws.com/foo/bar'))
        self.assertEqual(s3Info['request']['headers']['x-amz-acl'], 'private')

        # Test finalize for a single-chunk upload
        resp = self.request(path='/file/completion', method='POST',
                            user=self.admin,
                            params={'uploadId': resp.json['_id']})
        self.assertStatusOk(resp)
        self.assertFalse(resp.json['s3Verified'])
        self.assertEqual(resp.json['size'], 1024)
        self.assertEqual(resp.json['assetstoreId'], str(assetstore['_id']))
        self.assertTrue('s3Key' in resp.json)
        self.assertTrue(resp.json['fullpath'].startswith(
            'https://bucketname.s3.amazonaws.com/foo/bar/'))

        # Test init for a multi-chunk upload
        params['size'] = 1024 * 1024 * 1024 * 5
        resp = self.request(path='/file', method='POST', user=self.admin,
                            params=params)
        self.assertStatusOk(resp)

        s3Info = resp.json['s3']
        self.assertEqual(s3Info['chunked'], True)
        self.assertEqual(type(s3Info['chunkLength']), int)
        self.assertEqual(s3Info['request']['method'], 'POST')
        self.assertTrue(s3Info['request']['url'].startswith(
                        'https://bucketname.s3.amazonaws.com/foo/bar'))

        # Test init for an empty file (should be no-op)
        params['size'] = 0
        resp = self.request(path='/file', method='POST', user=self.admin,
                            params=params)
        self.assertStatusOk(resp)
        self.assertFalse('behavior' in resp.json)
        self.assertFalse('s3' in resp.json)
