from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder.models.user import User
from girder.settings import SettingKey
from tests import base

from girder_authorized_upload.constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD


def setUpModule():
    base.enabledPlugins.append('authorized_upload')
    base.startServer()


def tearDownModule():
    base.stopServer()


class AuthorizedUploadTest(base.TestCase):
    def setUp(self):
        super().setUp()

        self.admin = User().createUser(
            login='admin',
            password='passwd',
            firstName='admin',
            lastName='admin',
            email='admin@admin.org'
        )

        for folder in Folder().childFolders(parent=self.admin, parentType='user', user=self.admin):
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

    def testAuthorizedUpload(self):
        Setting().set(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE, 1)

        # Anon access should not work
        resp = self.request('/authorized_upload', method='POST', params={
            'folderId': self.privateFolder['_id']
        })
        self.assertStatus(resp, 401)

        # Create our secure URL
        resp = self.request('/authorized_upload', method='POST', user=self.admin, params={
            'folderId': self.privateFolder['_id']
        })
        self.assertStatusOk(resp)
        parts = resp.json['url'].rsplit('/', 3)
        tokenId, folderId = parts[-1], parts[-2]

        token = Token().load(tokenId, force=True, objectId=False)

        self.assertIsNotNone(token)
        self.assertEqual(folderId, str(self.privateFolder['_id']))
        self.assertEqual(set(token['scope']), {
            TOKEN_SCOPE_AUTHORIZED_UPLOAD,
            'authorized_upload_folder_%s' % self.privateFolder['_id']
        })

        # Make sure this token doesn't let us upload into a different folder
        params = {
            'parentType': 'folder',
            'parentId': self.publicFolder['_id'],
            'name': 'hello.txt',
            'size': 11,
            'mimeType': 'text/plain'
        }

        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatus(resp, 401)

        # Initialize upload into correct folder
        params['parentId'] = self.privateFolder['_id']
        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatusOk(resp)

        # We should remove the scope that allows further uploads
        upload = Upload().load(resp.json['_id'])
        token = Token().load(tokenId, force=True, objectId=False)
        self.assertEqual(token['scope'], [
            'authorized_upload_folder_%s' % self.privateFolder['_id']
        ])

        # Authorized upload ID should be present in the token
        self.assertEqual(token['authorizedUploadId'], upload['_id'])

        # Attempting to initialize new uploads using the token should fail
        resp = self.request(path='/file', method='POST', params=params, token=tokenId)
        self.assertStatus(resp, 401)

        # Uploading a chunk should work with the token
        resp = self.request(
            path='/file/chunk', method='POST', token=tokenId, body='hello ', params={
                'uploadId': str(upload['_id'])
            }, type='text/plain')
        self.assertStatusOk(resp)

        # Requesting our offset should work with the token
        # The offset should not have changed
        resp = self.request(path='/file/offset', method='GET', token=tokenId, params={
            'uploadId': upload['_id']
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['offset'], 6)

        # Upload the second chunk
        resp = self.request(
            path='/file/chunk', method='POST', token=tokenId, body='world', params={
                'offset': 6,
                'uploadId': str(upload['_id'])
            }, type='text/plain')
        self.assertStatusOk(resp)

        # Trying to upload more chunks should fail
        resp = self.request(
            path='/file/chunk', method='POST', token=tokenId, body='extra', params={
                'offset': 11,
                'uploadId': str(upload['_id'])
            }, type='text/plain')
        self.assertStatus(resp, 401)

        # The token should be destroyed
        self.assertIsNone(Token().load(tokenId, force=True, objectId=False))
