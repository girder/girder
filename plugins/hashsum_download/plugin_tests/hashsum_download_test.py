# -*- coding: utf-8 -*-
import hashlib
import io
import time

from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.models.user import User
from tests import base

import girder_hashsum_download as hashsum_download


def setUpModule():
    base.enabledPlugins.append('hashsum_download')
    base.startServer()


def tearDownModule():
    base.stopServer()


class HashsumDownloadTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self, assetstoreType='filesystem')

        # Two users are created (user and otherUser).
        # A hierarchy is created as is:
        #  - user:
        #       |- [Folder (public)] publicFolder:
        #           |- publicFile
        #           |- duplicatePublicFile
        #       |- [Folder (private)] private:
        #           |- privateFile
        #           |- privateOnlyFile
        #
        #  - otherUser:
        #       |- (nothing)
        #
        # In summary, user has access to all the files and otherUser to none.

        self.user = User().createUser(
            login='leeloo',
            password='multipass',
            firstName='Leeloominai',
            lastName='Sebat',
            email='quinque@universe.test'
        )

        for folder in Folder().childFolders(parent=self.user, parentType='user', user=self.user):
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        self.userData = u'\u266a Il dolce suono mi ' \
                        u'colp\u00ec di sua voce! \u266a'.encode('utf8')
        self.privateFile = Upload().uploadFromFile(
            obj=io.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PRIVATE',
            parentType='folder',
            parent=self.privateFolder,
            user=self.user,
            mimeType='audio/mp4'
        )
        self.publicFile = Upload().uploadFromFile(
            obj=io.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PUBLIC',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user,
            mimeType='audio/flac'
        )
        self.duplicatePublicFile = Upload().uploadFromFile(
            obj=io.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PUBLIC DUPLICATE',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user,
            mimeType='audio/mp3'
        )

        self.privateOnlyData =\
            u'\u2641 \u2600 \u2601 \u2614 \u2665'.encode('utf8')
        self.privateOnlyFile = Upload().uploadFromFile(
            obj=io.BytesIO(self.privateOnlyData),
            size=len(self.privateOnlyData),
            name='Powers combined',
            parentType='folder',
            parent=self.privateFolder,
            user=self.user,
            mimeType='image/png'
        )

        self.otherUser = User().createUser(
            login='zorg',
            password='mortis',
            firstName='Jean-Baptiste',
            lastName='Zorg',
            email='nullus@universe.test'
        )

    @staticmethod
    def _hashSum(value, algorithm):
        hasher = hashlib.new(algorithm)
        hasher.update(value)
        return hasher.hexdigest()

    def _download(self, hashValue, hashAlgorithm,
                  user=None, params=None, additionalHeaders=None):
        return self.request(
            path='/file/hashsum/%s/%s/download' % (hashAlgorithm, hashValue),
            method='GET',
            user=user,
            params=params,
            additionalHeaders=additionalHeaders,
            isJson=False
        )

    def _testNormalUse(self, hashValue, hashAlgorithm, file, data, user=None):
        resp = self._download(hashValue, hashAlgorithm, user=user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
        self.assertEqual(resp.headers['Content-Length'], file['size'])
        self.assertEqual(resp.headers['Content-Type'], file['mimeType'])
        self.assertEqual(resp.headers['Content-Disposition'],
                         'attachment; filename="%s"' % file['name'])
        self.assertEqual(resp.headers['Content-Type'], file['mimeType'])
        self.assertEqual(data, self.getBody(resp, text=False))

    def testDownload(self):
        # Test an invalid algorithm
        resp = self._download('crc32', '1a2b3c4d', user=self.user)
        self.assertStatus(resp, 400)

        for hashAlgorithm in ['sha512']:
            publicDataHash = self._hashSum(self.userData, hashAlgorithm)
            privateDataHash = self._hashSum(self.privateOnlyData, hashAlgorithm)

            # Test normal use
            for hashValue in [publicDataHash.lower(), publicDataHash.upper()]:
                for algo in [hashAlgorithm.lower(), hashAlgorithm.upper()]:
                    self._testNormalUse(
                        hashValue, algo, self.publicFile, self.userData
                    )

            # Test a non-existent file (in this case, one that's empty)
            empty_hash = self._hashSum(b'', hashAlgorithm)
            resp = self._download(empty_hash, hashAlgorithm)
            self.assertStatus(resp, 404)

            # Test a private file anonymously
            resp = self._download(privateDataHash, hashAlgorithm)
            self.assertStatus(resp, 404)

            # Test a private file when unauthorized
            resp = self._download(
                privateDataHash, hashAlgorithm, user=self.otherUser
            )
            self.assertStatus(resp, 404)

            # Test a private file when authorized
            resp = self._download(
                privateDataHash, hashAlgorithm, user=self.user
            )
            self.assertStatusOk(resp)
            self.assertEqual(
                self.privateOnlyData, self.getBody(resp, text=False))

            # Test for a file that exists in both public and private folder
            # while logged in.
            self._testNormalUse(
                publicDataHash,
                hashAlgorithm,
                self.privateFile,
                self.userData,
                user=self.user
            )

            # Test specified content dispositions
            for contentDisposition in ['attachment', 'inline']:
                disposition = {
                    'contentDisposition': contentDisposition
                }
                resp = self._download(
                    publicDataHash, hashAlgorithm, params=disposition
                )
                self.assertStatusOk(resp)
                self.assertEqual(resp.headers['Content-Disposition'],
                                 '%s; filename="%s"' %
                                 (contentDisposition, self.publicFile['name']))
                self.assertEqual(self.userData,
                                 self.getBody(resp, text=False))

            # Test downloading with an offset
            resp = self._download(
                publicDataHash, hashAlgorithm, params={'offset': 15})
            self.assertStatus(resp, 206)
            self.assertEqual(self.userData[15:],
                             self.getBody(resp, text=False))

            # Test downloading with a range header and query range params
            respHeader = self._download(
                publicDataHash, hashAlgorithm,
                additionalHeaders=[('Range', 'bytes=10-29')]
            )
            respQuery = self._download(
                publicDataHash, hashAlgorithm,
                params={'offset': 10, 'endByte': 30}
            )
            for resp in [respHeader, respQuery]:
                self.assertStatus(resp, 206)
                self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
                self.assertEqual(resp.headers['Content-Length'], 30 - 10)
                self.assertEqual(resp.headers['Content-Range'],
                                 'bytes 10-29/%d' % len(self.userData))
                self.assertEqual(resp.headers['Content-Type'],
                                 self.publicFile['mimeType'])
                self.assertEqual(self.userData[10:30],
                                 self.getBody(resp, text=False))

    def testKeyFile(self):
        # Make sure sha512 appears in returned file documents
        resp = self.request('/file/%s' % self.publicFile['_id'])
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['sha512'], self.publicFile['sha512'])

        template = '/file/%s/hashsum_file/%s'

        # Test with bad algo
        resp = self.request(template % (self.publicFile['_id'], 'foo'))
        self.assertStatus(resp, 400)
        self.assertRegex(resp.json['message'], '^Invalid value for algo: "foo"')

        # Should work with public file
        resp = self.request(template % (self.publicFile['_id'], 'sha512'),
                            isJson=False)
        self.assertStatusOk(resp)
        respBody = self.getBody(resp)
        self.assertEqual(respBody, '%s\n' % self.publicFile['sha512'])
        self.assertEqual(len(respBody), 129)

        # Should not work with private file
        resp = self.request(template % (self.privateFile['_id'], 'sha512'))
        self.assertStatus(resp, 401)
        self.assertRegex(resp.json['message'], '^Read access denied')

    def testAutoComputeHashes(self):
        with self.assertRaises(ValidationException):
            Setting().set(hashsum_download.PluginSettings.AUTO_COMPUTE, 'bad')

        old = hashsum_download.SUPPORTED_ALGORITHMS
        hashsum_download.SUPPORTED_ALGORITHMS = {'sha512', 'sha256'}
        Setting().set(hashsum_download.PluginSettings.AUTO_COMPUTE, True)

        file = Upload().uploadFromFile(
            obj=io.BytesIO(self.userData), size=len(self.userData), name='Another file',
            parentType='folder', parent=self.privateFolder, user=self.user)

        start = time.time()
        while time.time() < start + 15:
            file = File().load(file['_id'], force=True)
            if 'sha256' in file:
                break
            time.sleep(0.2)

        expected = hashlib.sha256()
        expected.update(self.userData)
        self.assertIn('sha256', file)
        self.assertEqual(file['sha256'], expected.hexdigest())

        expected = hashlib.sha512()
        expected.update(self.userData)
        self.assertIn('sha512', file)
        self.assertEqual(file['sha512'], expected.hexdigest())

        hashsum_download.SUPPORTED_ALGORITHMS = old

    def testManualComputeHashes(self):
        Setting().set(hashsum_download.PluginSettings.AUTO_COMPUTE, False)
        old = hashsum_download.SUPPORTED_ALGORITHMS
        hashsum_download.SUPPORTED_ALGORITHMS = {'sha512', 'sha256'}

        self.assertNotIn('sha256', self.privateFile)

        expected = hashlib.sha256()
        expected.update(self.userData)

        # Running the compute endpoint should only compute the missing ones
        resp = self.request(
            '/file/%s/hashsum' % self.privateFile['_id'], method='POST', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, {
            'sha256': expected.hexdigest()
        })

        # Running again should be a no-op
        resp = self.request(
            '/file/%s/hashsum' % self.privateFile['_id'], method='POST', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

        file = File().load(self.privateFile['_id'], force=True)
        self.assertEqual(file['sha256'], expected.hexdigest())

        hashsum_download.SUPPORTED_ALGORITHMS = old

    def testGetByHash(self):
        hashAlgorithm = 'sha512'
        publicDataHash = self._hashSum(self.userData, hashAlgorithm)
        privateDataHash = self._hashSum(self.privateOnlyData, hashAlgorithm)

        # There are three files with publicDataHash for self.user .
        resp = self.request(
            '/file/hashsum/%s/%s' % (hashAlgorithm, publicDataHash), user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        for file in resp.json:
            self.assertEqual(file['sha512'], publicDataHash)

        # There is one file with privateDataHash for self.user .
        resp = self.request(
            '/file/hashsum/%s/%s' % (hashAlgorithm, privateDataHash), user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        for file in resp.json:
            self.assertEqual(file['sha512'], privateDataHash)

        # There are two files with publicDataHash for self.otherUser .
        # There is one private file with this hash that otherUser lacks access to.
        resp = self.request(
            '/file/hashsum/%s/%s' % (hashAlgorithm, publicDataHash), user=self.otherUser)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        for file in resp.json:
            self.assertEqual(file['sha512'], publicDataHash)

        # No files with privateDataHash for self.otherUser .
        resp = self.request(
            '/file/hashsum/%s/%s' % (hashAlgorithm, privateDataHash), user=self.otherUser)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)
