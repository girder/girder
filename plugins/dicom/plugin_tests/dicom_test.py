#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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
import dicom
import six
from tests import base
import time
from girder import events
from girder.constants import AccessType


def setUpModule():
    base.enabledPlugins.append('dicom')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DicomTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        # First setup users
        user = {
            'email': 'jane.doe@email.com',
            'login': 'jane-doe',
            'firstName': 'Jane',
            'lastName': 'Doe',
            'password': 'password'
        }
        self.user = self.model('user').createUser(**user)
        folders = self.model('folder').childFolders(
            parent=self.user, parentType='user', user=self.user)
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        # Open dcm file.
        self.dcmFilePath = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'],
            'plugins',
            'dicom',
            'DICOM-CT.dcm'
        )
        self.assertTrue(os.path.exists(self.dcmFilePath))
        self.dcm = dicom.read_file(self.dcmFilePath)

        # Upload the dicom file
        with open(self.dcmFilePath, 'r') as file:
            self.dcmData = file.read()
        self.assertTrue(self.dcmData)

        self.dcmFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(self.dcmData),
            size=len(self.dcmData),
            name='My DICOM file',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user,
            mimeType='dicom'
        )

        # Wait a little while to make sure the metadata is appended to the item
        starttime = time.time()
        while (not events.daemon.eventQueue.empty() and
                time.time() - starttime < 10):
            time.sleep(0.1)

        self.dcmItem = self.model('item').load(
            self.dcmFile['itemId'],
            level=AccessType.READ,
            user=self.user
        )
        self.assertHasKeys(self.dcmItem, ['meta'])

    def testDICOMHandler(self):
        metadata = self.dcmItem['meta']
        self.assertHasKeys(
            metadata,
            ['PatientName', 'PatientID', 'Modality', 'Study Date']
        )
        self.assertEqual(metadata['PatientName'], self.dcm.PatientName)
        self.assertEqual(metadata['PatientID'], self.dcm.PatientID)
        self.assertEqual(metadata['Modality'], self.dcm.Modality)
        self.assertEqual(metadata['Study Date'], self.dcm.StudyDate)
