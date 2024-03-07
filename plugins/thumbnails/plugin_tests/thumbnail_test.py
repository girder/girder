import io
import json
import os
import time

from tests import base
from girder import events
from girder.constants import ROOT_DIR
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.upload import Upload
from girder.models.user import User
from girder_jobs.constants import JobStatus
from PIL import Image


def setUpModule():
    base.enabledPlugins.append('thumbnails')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ThumbnailsTestCase(base.TestCase):
    def setUp(self):
        super().setUp()

        # Create some test documents with an item
        admin = {
            'email': 'admin@girder.test',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
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

        folders = Folder().childFolders(parent=self.admin, parentType='user', user=self.admin)
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        path = os.path.join(ROOT_DIR, 'girder', 'web', 'public', 'Girder_Mark.png')
        with open(path, 'rb') as file:
            self.image = file.read()
        events.unbind('thumbnails.create', 'test')

    def testThumbnailCreation(self):
        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.png',
                'size': len(self.image)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        resp = self.request(
            path='/file/chunk', method='POST', user=self.admin, body=self.image, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        params = {
            'fileId': fileId,
            'width': 64,
            'attachToId': str(self.admin['_id']),
            'attachToType': 'user'
        }

        # We shouldn't be able to add thumbnails without write access to the
        # target resource.
        resp = self.request(path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 403)

        # Should complain if we don't pass a width or a height
        del params['width']
        params['attachToId'] = str(self.user['_id'])

        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You must specify a valid width, height, or both.')

        # Set a width, we should now correctly have a thumbnail
        params['width'] = 64
        resp = self.request(path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        job = resp.json

        self.assertEqual(job['status'], JobStatus.SUCCESS)

        self.user = User().load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 1)
        thumbnailId = self.user['_thumbnails'][0]

        resp = self.request('/file/%s/download' % str(thumbnailId), isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (64, 64))

        # Delete the thumbnail, it should be removed from the user thumb list
        resp = self.request('/file/%s' % str(thumbnailId), method='DELETE', user=self.user)
        self.assertStatusOk(resp)

        self.assertEqual(File().load(thumbnailId), None)
        self.user = User().load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 0)

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)
        self.publicFolder = Folder().load(self.publicFolder['_id'], force=True)
        self.assertEqual(len(self.publicFolder['_thumbnails']), 1)

        thumbnailId = self.publicFolder['_thumbnails'][0]

        resp = self.request('/file/%s/download' % thumbnailId, isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (64, 32))

        # Deleting the public folder should delete the thumbnail as well
        Folder().remove(self.publicFolder)
        self.assertEqual(File().load(thumbnailId), None)

    def testDicomThumbnailCreation(self):
        path = os.path.join(ROOT_DIR, 'plugins', 'thumbnails', 'plugin_tests', 'data',
                            'sample_dicom.dcm')
        with open(path, 'rb') as file:
            data = file.read()

        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.dcm',
                'size': len(data)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        resp = self.request(
            path='/file/chunk', method='POST', user=self.admin, body=data, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        params = {
            'fileId': fileId,
            'width': 64,
            'attachToId': str(self.admin['_id']),
            'attachToType': 'user'
        }

        # We shouldn't be able to add thumbnails without write access to the
        # target resource.
        resp = self.request(path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 403)

        # Should complain if we don't pass a width or a height
        del params['width']
        params['attachToId'] = str(self.user['_id'])

        resp = self.request(path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You must specify a valid width, height, or both.')

        # Set a width, we should now correctly have a thumbnail
        params['width'] = 64
        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        job = resp.json

        self.assertEqual(job['status'], JobStatus.SUCCESS)

        self.user = User().load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 1)
        thumbnailId = self.user['_thumbnails'][0]

        resp = self.request('/file/%s/download' % thumbnailId, isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (64, 64))

        # Delete the thumbnail, it should be removed from the user thumb list
        resp = self.request('/file/%s' % str(thumbnailId), method='DELETE', user=self.user)
        self.assertStatusOk(resp)

        self.assertEqual(File().load(thumbnailId), None)
        self.user = User().load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 0)

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)
        self.publicFolder = Folder().load(self.publicFolder['_id'], force=True)
        self.assertEqual(len(self.publicFolder['_thumbnails']), 1)

        thumbnailId = self.publicFolder['_thumbnails'][0]

        resp = self.request('/file/%s/download' % thumbnailId, isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(io.BytesIO(data))
        self.assertEqual(image.size, (64, 32))

        # Deleting the public folder should delete the thumbnail as well
        Folder().remove(self.publicFolder)
        self.assertEqual(File().load(thumbnailId), None)

    def testCreateThumbnailOverride(self):
        def override(event):
            # Override thumbnail creation -- just grab the first 4 bytes
            self.assertIn('file', event.info)

            streamFn = event.info['streamFn']
            stream = streamFn()
            contents = b''.join(stream())

            uploadModel = Upload()

            upload = uploadModel.createUpload(
                user=self.admin, name='magic', parentType=None, parent=None,
                size=4)

            thumbnail = uploadModel.handleChunk(upload, contents[:4])

            event.addResponse({
                'file': thumbnail
            })
            event.preventDefault()

        events.bind('thumbnails.create', 'test', override)

        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.png',
                'size': len(self.image)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        resp = self.request(
            path='/file/chunk', method='POST', user=self.admin, body=self.image, params={
                'uploadId': uploadId
            }, type='text/plain')
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)

        # Download the new thumbnail
        folder = Folder().load(self.publicFolder['_id'], force=True)
        self.assertEqual(len(folder['_thumbnails']), 1)
        thumbnail = File().load(folder['_thumbnails'][0], force=True)

        self.assertEqual(thumbnail['attachedToType'], 'folder')
        self.assertEqual(thumbnail['attachedToId'], folder['_id'])

        # Its contents should be the PNG magic number
        stream = File().download(thumbnail, headers=False)
        self.assertEqual(b'\x89PNG', b''.join(stream()))

    def testCreationOnUpload(self):
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.png',
                'size': len(self.image),
                'reference': json.dumps({
                    'thumbnail': {
                        'width': 100
                    }
                })
            })
        self.assertStatusOk(resp)

        resp = self.request(
            path='/file/chunk', method='POST', user=self.admin, body=self.image, params={
                'offset': 0,
                'uploadId': resp.json['_id']
            }, type='image/png')
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        itemId = resp.json['itemId']

        start = time.time()
        while time.time() - start < 15:
            # Wait for thumbnail creation
            item = Item().load(itemId, force=True)
            if item.get('_thumbnails'):
                break
            time.sleep(0.1)
        self.assertEqual(len(item['_thumbnails']), 1)
        file = File().load(item['_thumbnails'][0], force=True)
        with File().open(file) as fh:
            self.assertEqual(fh.read(2), b'\xff\xd8')  # jpeg magic number
