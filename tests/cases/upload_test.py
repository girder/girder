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

import json
import os
import re
import requests
import six
import threading

from girder import events
from girder.utility import assetstore_utilities

from .. import base
from .. import mongo_replicaset
from girder.utility.s3_assetstore_adapter import botoConnectS3


Chunk1, Chunk2 = ('hello ', 'world')


def setUpModule():
    base.startServer(mockS3=True)


def tearDownModule():
    base.stopServer()


def _send_s3_request(request, data=None):
    """
    Send a request to an S3 server.
    :param request: a dictionary of headers, method, and url.
    :param data: data to include in the request.
    :returns: the result of the request.
    """
    if request['method'] == 'PUT':
        req = requests.put(url=request['url'], data=data,
                           headers=request.get('headers', {}))
    elif request['method'] == 'POST':
        req = requests.post(url=request['url'], data=data,
                            headers=request.get('headers', {}))
    return req


class UploadTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'admin@email.com',
            'login': 'admin',
            'firstName': 'Admin',
            'lastName': 'Admin',
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
        folders = self.model('folder').childFolders(
            parent=self.user, parentType='user', user=self.user)
        for folder in folders:
            if folder['public'] is True:
                self.folder = folder

    def _uploadFile(self, name, partial=False, largeFile=False):
        """
        Upload a file either completely or partially.
        :param name: the name of the file to upload.
        :param partial: the number of steps to complete in the uploads: 0
                        initializes the upload, 1 uploads 1 chunk, etc.  False
                        to complete the upload.
        :param largeFile: if True, upload a file that is > 32Mb
        :returns: the upload record which includes the upload id.
        """
        if not largeFile:
            chunk1 = Chunk1
            chunk2 = Chunk2
        else:
            chunk1 = '-' * (1024 * 1024 * 32)
            chunk2 = '-' * (1024 * 1024 * 1)
        resp = self.request(
            path='/file', method='POST', user=self.user, params={
                'parentType': 'folder',
                'parentId': self.folder['_id'],
                'name': name,
                'size': len(chunk1) + len(chunk2),
                'mimeType': 'text/plain'
            })
        self.assertStatusOk(resp)
        upload = resp.json
        if partial is not False and partial == 0:
            return upload
        if 's3' not in upload:
            fields = [('offset', 0), ('uploadId', upload['_id'])]
            files = [('chunk', 'helloWorld.txt', chunk1)]
            resp = self.multipartRequest(
                path='/file/chunk', user=self.user, fields=fields, files=files)
            self.assertStatusOk(resp)
            if partial is not False:
                return resp.json
            fields = [('offset', len(chunk1)), ('uploadId', upload['_id'])]
            files = [('chunk', 'helloWorld.txt', chunk2)]
            resp = self.multipartRequest(
                path='/file/chunk', user=self.user, fields=fields, files=files)
            self.assertStatusOk(resp)
            return upload
        # s3 uses a different method for uploading chunks
        # This has no error checking at all
        if not upload['s3']['chunked']:
            _send_s3_request(upload['s3']['request'], chunk1+chunk2)
            if partial is not False:
                return
        else:
            chunk1 = chunk1+chunk2
            s3resp = _send_s3_request(upload['s3']['request'])
            matches = re.search('<UploadId>(.*)</UploadId>', s3resp.text)
            s3uploadId = matches.groups()[0]
            offset = 0
            chunkN = 1
            while len(chunk1):
                params = {'offset': offset, 'uploadId': upload['_id']}
                params["chunk"] = json.dumps({'s3UploadId': s3uploadId,
                                              'partNumber': chunkN})
                resp = self.request(path='/file/chunk', method='POST',
                                    user=self.user, params=params)
                self.assertStatusOk(resp)
                upload = resp.json
                if len(chunk1) > upload['s3']['chunkLength']:
                    chunk2 = chunk1[upload['s3']['chunkLength']:]
                    chunk1 = chunk1[:upload['s3']['chunkLength']]
                else:
                    chunk2 = ""
                _send_s3_request(upload['s3']['request'], chunk1)
                chunk1 = chunk2
                if partial is not False:
                    partial -= 1
                chunkN += 1
                if partial is not False and not partial:
                    return upload
        resp = self.request(path='/file/completion', method='POST',
                            user=self.user,
                            params={'uploadId': upload['_id']})
        self.assertStatusOk(resp)
        if 's3FinalizeRequest' in resp.json:
            _send_s3_request(resp.json['s3FinalizeRequest'])
        return upload

    def _testUpload(self):
        """
        Upload a file to the server and several partial files.  Test that we
        can delete a partial upload but not a completed upload. Test that we
        can delete partial uploads that are older than a certain date.
        """
        completeUpload = self._uploadFile('complete_upload')
        # test uploading large files
        self._uploadFile('complete_upload', largeFile=True)
        partialUploads = []
        for largeFile in (False, True):
            for partial in range(3):
                partialUploads.append(self._uploadFile(
                    'partial_upload_%d_%s' % (partial, str(largeFile)),
                    partial, largeFile))
        # check that a user cannot list partial uploads
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.user)
        self.assertStatus(resp, 403)
        # The admin user should see all of the partial uploads, but not the
        # complete upload
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertStatusOk(resp)
        foundUploads = resp.json
        self.assertEqual(len(foundUploads), len(partialUploads))
        # The user shouldn't be able to delete an upload
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.user,
                            params={'uploadId': partialUploads[0]['_id']})
        self.assertStatus(resp, 403)
        # We shouldn't be able to delete the completed upload
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.admin,
                            params={'uploadId': completeUpload['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertEqual(len(resp.json), len(partialUploads))
        # The admin should be able to ask for a partial upload by id
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin,
                            params={'uploadId': partialUploads[0]['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], partialUploads[0]['_id'])
        # The admin should be able to ask for a partial upload by assetstore id
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin,
                            params={'assetstoreId': self.assetstore['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), len(partialUploads))
        # The admin should be able to ask for a partial upload by age.
        # Everything should be more than 0 days old
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin,
                            params={'minimumAge': 0})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), len(partialUploads))
        # The admin should be able to delete an upload
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.admin,
                            params={'uploadId': partialUploads[0]['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], partialUploads[0]['_id'])
        # We should now have one less partial upload
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertEqual(len(resp.json), len(partialUploads)-1)
        # If we ask to delete everything more than one day old, nothing should
        # be deleted.
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.admin,
                            params={'minimumAge': 1})
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])
        # Delete all partial uploads
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertEqual(resp.json, [])

    def testFilesystemAssetstoreUpload(self):
        self._testUpload()
        # Test that a delete during an upload still results in one file
        adapter = assetstore_utilities.getAssetstoreAdapter(self.assetstore)
        size = 101
        data = six.BytesIO(b' ' * size)
        files = []
        files.append(self.model('upload').uploadFromFile(
            data, size, 'progress', parentType='folder', parent=self.folder,
            assetstore=self.assetstore))
        fullPath0 = adapter.fullPath(files[0])
        conditionRemoveDone = threading.Condition()
        conditionInEvent = threading.Condition()

        def waitForCondition(*args, **kwargs):
            # Single that we are in the event and then wait to be told that
            # the delete has occured before returning.
            with conditionInEvent:
                conditionInEvent.notify()
            with conditionRemoveDone:
                conditionRemoveDone.wait()

        def uploadFileWithWait():
            size = 101
            data = six.BytesIO(b' ' * size)
            files.append(self.model('upload').uploadFromFile(
                data, size, 'progress', parentType='folder', parent=self.folder,
                assetstore=self.assetstore))

        events.bind('model.file.finalizeUpload.before', 'waitForCondition',
                    waitForCondition)
        # We create an upload that is bound to an event that waits during the
        # finalizeUpload.before event so that the remove will be executed
        # during this time.
        with conditionInEvent:
            t = threading.Thread(target=uploadFileWithWait)
            t.start()
            conditionInEvent.wait()
        self.assertTrue(os.path.exists(fullPath0))
        self.model('file').remove(files[0])
        # We shouldn't actually remove the file here
        self.assertTrue(os.path.exists(fullPath0))
        with conditionRemoveDone:
            conditionRemoveDone.notify()
        t.join()

        events.unbind('model.file.finalizeUpload.before', 'waitForCondition')
        fullPath1 = adapter.fullPath(files[0])
        self.assertEqual(fullPath0, fullPath1)
        self.assertTrue(os.path.exists(fullPath1))

    def testGridFSAssetstoreUpload(self):
        # Clear any old DB data
        base.dropGridFSDatabase('girder_test_upload_assetstore')
        # Clear the assetstore database and create a GridFS assetstore
        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        assetstore = self.model('assetstore').createGridFsAssetstore(
            name='Test', db='girder_test_upload_assetstore')
        self.assetstore = assetstore
        self._testUpload()

    def testGridFSReplicaSetAssetstoreUpload(self):
        verbose = 0
        if 'REPLICASET' in os.environ.get('EXTRADEBUG', '').split():
            verbose = 2
        # Starting the replica sets takes time (~25 seconds)
        mongo_replicaset.startMongoReplicaSet(verbose=verbose)
        # Clear the assetstore database and create a GridFS assetstore
        self.model('assetstore').remove(self.model('assetstore').getCurrent())
        # When the mongo connection to one of the replica sets goes down, it
        # takes twice the socket timeout for us to reconnect and get on with
        # an upload.  We can override the default timeout by passing it as a
        # mongodb uri parameter.
        assetstore = self.model('assetstore').createGridFsAssetstore(
            name='Test', db='girder_assetstore_rs_upload_test',
            mongohost='mongodb://127.0.0.1:27070,127.0.0.1:27071,'
            '127.0.0.1:27072/?socketTimeoutMS=5000&connectTimeoutMS=2500',
            replicaset='replicaset')
        self.assetstore = assetstore
        self._testUpload()
        # Test having the primary replica set going offline and then uploading
        # again.  If the current primary goes offline, it seems to take mongo
        # 30 seconds to elect a new primary.  If we step down the current
        # primary before pausing it, then the new election will happen in 20
        # seconds.
        mongo_replicaset.stepDownMongoReplicaSet(0)
        mongo_replicaset.waitForRSStatus(
            mongo_replicaset.getMongoClient(0), status=[2, (1, 2), (1, 2)],
            verbose=verbose)
        mongo_replicaset.pauseMongoReplicaSet([True], verbose=verbose)
        self._uploadFile('rs_upload_1')
        # Have a different member of the replica set go offline and the first
        # come back.  This takes a long time, so I am disabling it
        #  mongo_replicaset.pauseMongoReplicaSet([False, True], verbose=verbose)
        #  self._uploadFile('rs_upload_2')
        # Have the set come back online and upload once more
        mongo_replicaset.pauseMongoReplicaSet([False, False], verbose=verbose)
        self._uploadFile('rs_upload_3')
        mongo_replicaset.stopMongoReplicaSet()

    def testS3AssetstoreUpload(self):
        # Clear the assetstore database and create an S3 assetstore
        self.model('assetstore').remove(self.assetstore)
        params = {
            'name': 'S3 Assetstore',
            'bucket': 'bucketname',
            'prefix': 'testprefix',
            'accessKeyId': 'someKey',
            'secret': 'someSecret',
            'service': base.mockS3Server.service
        }
        assetstore = self.model('assetstore').createS3Assetstore(**params)
        self.assetstore = assetstore
        self._testUpload()
        # make an untracked upload to test that we can find and clear it
        conn = botoConnectS3(base.mockS3Server.botoConnect)
        bucket = conn.lookup(bucket_name='bucketname', validate=True)
        bucket.initiate_multipart_upload('testprefix/abandoned_upload')
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        # Ask to delete it
        resp = self.request(path='/system/uploads', method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        # Check that it is gone
        resp = self.request(path='/system/uploads', method='GET',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])
