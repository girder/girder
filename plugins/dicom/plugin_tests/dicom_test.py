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

from __future__ import print_function

import os
import dicom
import six
import threading
from tests import base
from girder import events
from girder.constants import AccessType


def setUpModule():
    base.enabledPlugins.append('dicom')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DicomTestCase(base.TestCase):
    def _waitForHandler(self, eventName, timeout=5):
        """
        Wait for plugin's data.process event handler to complete.
        :param eventName: the name of the event to wait for
        :param timeout: the time in seconds after which to stop waiting
        :returns: True if event occurred before timeout
        """
        event = threading.Event()

        def HandlerCallback(handlerEvent):
            event.set()

        handled = False
        with events.bound(eventName, 'waitForHandler', HandlerCallback):
            handled = event.wait(timeout)
        return handled

    def setUp(self):
        base.TestCase.setUp(self)

        # Add a user
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
            if folder['public']:
                self.publicFolder = folder
                break

    def testDICOMHandler(self):
        # Parse the dicom file
        self.dcmFilePath = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'],
            'plugins',
            'dicom',
            'DICOM-CT.dcm'
        )
        self.assertTrue(os.path.exists(self.dcmFilePath))
        self.dcm = dicom.read_file(self.dcmFilePath)

        # Upload the dicom file
        with open(self.dcmFilePath, 'rb') as file:
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

        # Wait for handler success event
        handled = self._waitForHandler(eventName='dicom.handler.success')
        self.assertTrue(handled)

        # Verify metadata
        self.dcmItem = self.model('item').load(
            self.dcmFile['itemId'],
            level=AccessType.READ,
            user=self.user
        )
        self.assertHasKeys(self.dcmItem, ['meta'])
        metadata = self.dcmItem['meta']
        expectedKeys = ['PatientName', 'PatientID', 'StudyID',
                        'StudyInstanceUID', 'StudyDate', 'StudyTime',
                        'SeriesInstanceUID', 'SeriesDate', 'SeriesTime',
                        'SeriesNumber', 'SOPInstanceUID', 'Modality']
        self.assertHasKeys(metadata, expectedKeys)
        self.assertEqual(metadata['PatientName'],
                         self.dcm.PatientName.encode('utf-8'))
        self.assertEqual(metadata['PatientID'], self.dcm.PatientID)
        self.assertEqual(metadata['StudyID'], self.dcm.StudyID)
        self.assertEqual(metadata['StudyInstanceUID'],
                         self.dcm.StudyInstanceUID)
        self.assertEqual(metadata['StudyDate'], self.dcm.StudyDate)
        self.assertEqual(metadata['StudyTime'], self.dcm.StudyTime)
        self.assertEqual(metadata['SeriesInstanceUID'],
                         self.dcm.SeriesInstanceUID)
        self.assertEqual(metadata['SeriesDate'], self.dcm.SeriesDate)
        self.assertEqual(metadata['SeriesTime'], self.dcm.SeriesTime)
        self.assertEqual(metadata['SeriesNumber'], self.dcm.SeriesNumber)
        self.assertEqual(metadata['SOPInstanceUID'], self.dcm.SOPInstanceUID)
        self.assertEqual(metadata['Modality'], self.dcm.Modality)

    def testDICOMHandlerInvalid(self):
        # Upload non-DICOM data
        data = b'data'
        self.dcmFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(data),
            size=len(data),
            name='data',
            parentType='folder',
            parent=self.publicFolder,
            user=self.user
        )

        # Wait for handler ignore event
        handled = self._waitForHandler(eventName='dicom.handler.ignore')
        self.assertTrue(handled)
