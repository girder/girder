#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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

import six
import hashlib

from tests import base


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

        self.user = self.model('user').createUser(
            login='leeloo',
            password='multipass',
            firstName='Leeloominai',
            lastName='Sebat',
            email='quinque@universe.org'
        )

        for folder in self.model('folder').childFolders(
                parent=self.user, parentType='user', user=self.user):
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        self.userData = u'\u266a Il dolce suono mi ' \
                        u'colp\u00ec di sua voce! \u266a'.encode('utf8')
        self.privateFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PRIVATE',
            parentType='folder',
            parent=self.privateFolder,
            user=self.user,
            mimeType='audio/mp4'
        )
        self.publicFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PUBLIC',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user,
            mimeType='audio/flac'
        )
        self.duplicatePublicFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(self.userData),
            size=len(self.userData),
            name='Il dolce suono - PUBLIC DUPLICATE',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user,
            mimeType='audio/mp3'
        )

        self.privateOnlyData =\
            u'\u2641 \u2600 \u2601 \u2614 \u2665'.encode('utf8')
        self.privateOnlyFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(self.privateOnlyData),
            size=len(self.privateOnlyData),
            name='Powers combined',
            parentType='folder',
            parent=self.privateFolder,
            user=self.user,
            mimeType='image/png'
        )

        self.otherUser = self.model('user').createUser(
            login='zorg',
            password='mortis',
            firstName='Jean-Baptiste',
            lastName='Zorg',
            email='nullus@universe.org'
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
        six.assertRegex(self, resp.json['message'], '^Invalid algorithm "foo"')

        # Should work with public file
        resp = self.request(template % (self.publicFile['_id'], 'sha512'),
                            isJson=False)
        self.assertStatusOk(resp)
        hash = self.getBody(resp)
        self.assertEqual(hash, self.publicFile['sha512'])
        self.assertEqual(len(hash), 128)

        # Should not work with private file
        resp = self.request(template % (self.privateFile['_id'], 'sha512'))
        self.assertStatus(resp, 401)
        six.assertRegex(self, resp.json['message'], '^Read access denied')
