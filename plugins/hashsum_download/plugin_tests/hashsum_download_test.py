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

    def testDownload(self):
        # Test an invalid algorithm
        resp = self.request(
            path='/file/hashsum/%s/%s/download' % ('crc32', '1a2b3c4d'),
            method='GET', user=self.user, isJson=False,
        )
        self.assertStatus(resp, 400)

        for hashAlgorithm in ['sha512']:
            publicDataHash = self._hashSum(self.userData, hashAlgorithm)
            privateDataHash = self._hashSum(self.privateOnlyData, hashAlgorithm)

            # Test normal use
            for hashValue in [
                publicDataHash.lower(),
                publicDataHash.upper()
            ]:
                resp = self.request(
                    path='/file/hashsum/%s/%s/download' % (
                        hashAlgorithm, hashValue),
                    method='GET', isJson=False)
                self.assertStatusOk(resp)
                self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
                self.assertEqual(resp.headers['Content-Disposition'],
                                 'attachment; filename="%s"' %
                                 self.publicFile['name'])
                self.assertEqual(resp.headers['Content-Length'],
                                 self.publicFile['size'])
                self.assertEqual(resp.headers['Content-Type'],
                                 self.publicFile['mimeType'])
                self.assertEqual(resp.headers['Content-Disposition'],
                                 'attachment; filename="%s"' %
                                 self.publicFile['name'])
                self.assertEqual(self.userData,
                                 self.getBody(resp, text=False))

                # Also test upper case hashAlgorithm
                otherResp = self.request(
                    path='/file/hashsum/%s/%s/download' % (
                        hashAlgorithm.upper(), hashValue),
                    method='GET', isJson=False)
                self.assertStatusOk(otherResp)
                self.assertEqual(self.userData,
                                 self.getBody(otherResp, text=False))

            # Test a non-existent file (in this case, one that's empty)
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm,
                    self._hashSum(b'', hashAlgorithm)),
                method='GET', isJson=False)
            self.assertStatus(resp, 404)

            # Test a private file anonymously
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, privateDataHash),
                method='GET', user=None, isJson=False)
            self.assertStatus(resp, 404)

            # Test a private file when unauthorized
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, privateDataHash),
                method='GET', user=self.otherUser, isJson=False)
            self.assertStatus(resp, 404)

            # Test a private file when authorized
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, privateDataHash),
                method='GET', user=self.user, isJson=False)
            self.assertStatusOk(resp)
            self.assertEqual(
                self.privateOnlyData, self.getBody(resp, text=False))

            # Test for a file that exists in both public and private folder
            # while logged in.
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, publicDataHash),
                method='GET', user=self.user, isJson=False)
            self.assertStatusOk(resp)
            self.assertEqual(resp.headers['Content-Length'],
                             self.privateFile['size'])
            self.assertEqual(resp.headers['Content-Type'],
                             self.privateFile['mimeType'])
            self.assertEqual(resp.headers['Content-Disposition'],
                             'attachment; filename="%s"' %
                             self.privateFile['name'])
            self.assertEqual(self.userData,
                             self.getBody(resp, text=False))

            # Test specified content dispositions
            for contentDisposition in ['attachment', 'inline']:
                resp = self.request(
                    path='/file/hashsum/%s/%s/download' % (
                        hashAlgorithm, publicDataHash),
                    method='GET', isJson=False, params={
                        'contentDisposition': contentDisposition
                    })
                self.assertStatusOk(resp)
                self.assertEqual(resp.headers['Content-Disposition'],
                                 '%s; filename="%s"' %
                                 (contentDisposition, self.publicFile['name']))
                self.assertEqual(self.userData,
                                 self.getBody(resp, text=False))

            # Test downloading with an offset
            resp = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, publicDataHash),
                method='GET', isJson=False, params={
                    'offset': 15})
            self.assertStatus(resp, 206)
            self.assertEqual(self.userData[15:],
                             self.getBody(resp, text=False))

            # Test downloading with a range header and query range params
            respHeader = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, publicDataHash),
                method='GET', isJson=False, additionalHeaders=[
                    ('Range', 'bytes=10-29')])
            respQuery = self.request(
                path='/file/hashsum/%s/%s/download' % (
                    hashAlgorithm, publicDataHash),
                method='GET', isJson=False, params={
                    'offset': 10, 'endByte': 30})
            for resp in [respHeader, respQuery]:
                self.assertStatus(resp, 206)
                self.assertEqual(resp.headers['Accept-Ranges'], 'bytes')
                self.assertEqual(resp.headers['Content-Length'], 30 - 10)
                self.assertEqual(resp.headers['Content-Range'],
                                 'bytes 10-29/%d' % len(self.userData))
                self.assertEqual(self.userData[10:30],
                                 self.getBody(resp, text=False))
