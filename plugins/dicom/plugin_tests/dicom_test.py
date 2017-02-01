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
import six
from tests import base
from girder.constants import AccessType
from utils.event_helper import EventHelper


def setUpModule():
    base.enabledPlugins.append('dicom')
    base.startServer()


def tearDownModule():
    base.stopServer()


class DicomTestCase(base.TestCase):
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

    def tearDown(self):
        base.TestCase.tearDown(self)

        # Remove user
        self.model('user').remove(self.user)

    def testDICOMHandler(self):
        filename = 'Image0075.dcm'

        # Parse the dicom file
        dcmFilePath = os.path.join(
            os.environ['GIRDER_TEST_DATA_PREFIX'],
            'plugins',
            'dicom',
            filename
        )
        self.assertTrue(os.path.exists(dcmFilePath))

        # Upload the dicom file
        with open(dcmFilePath, 'rb') as file:
            dcmData = file.read()
        self.assertTrue(dcmData)

        with EventHelper('dicom.handler.success') as helper:
            dcmFile = self.model('upload').uploadFromFile(
                obj=six.BytesIO(dcmData),
                size=len(dcmData),
                name=filename,
                parentType='folder',
                parent=self.publicFolder,
                user=self.user,
                mimeType='dicom'
            )
            self.assertIsNotNone(dcmFile)

            # Wait for handler success event
            handled = helper.wait()
            self.assertTrue(handled)

        # Verify metadata
        dcmItem = self.model('item').load(
            dcmFile['itemId'],
            level=AccessType.READ,
            user=self.user
        )
        self.assertIn('meta', dcmItem)
        metadata = dcmItem['meta']
        self.assertEqual(len(metadata), 326)

        expectedKeys = [
            '00080005',  # Specific Character Set
            '00080020',  # Study Date
            '00080030',  # Study Time
            '00080050',  # Accession Number
            '00080061',  # Modalities in Study
            '00080090',  # Referring Physician's Name
            '00100010',  # Patient's Name
            '00100020',  # Patient ID
            '00100030',  # Patient's Birth Date
            '00100040',  # Patient's Sex
            '0020000D',  # Study Instance UID
            '00200010',  # Study ID
            '00201206',  # Number of Study Related Series
            '00201208'   # Number of Study Related Instances
        ]

        # Check several data elements
        self.assertHasKeys(metadata, expectedKeys)

        self.assertHasKeys(metadata['00080005'], ('vr', 'Value'))
        self.assertEqual(metadata['00080005']['vr'], 'CS')
        self.assertEqual(metadata['00080005']['Value'], ['ISO_IR 100'])

        self.assertHasKeys(metadata['00080020'], ('vr', 'Value'))
        self.assertEqual(metadata['00080020']['vr'], 'DA')
        self.assertEqual(metadata['00080020']['Value'], ['20030625'])

        self.assertHasKeys(metadata['00080030'], ('vr', 'Value'))
        self.assertEqual(metadata['00080030']['vr'], 'TM')
        self.assertEqual(metadata['00080030']['Value'], ['152734'])

        self.assertIn('vr', metadata['00080050'])
        self.assertNotIn('Value', metadata['00080050'])
        self.assertEqual(metadata['00080050']['vr'], 'SH')

        self.assertIn('vr', metadata['00080090'])
        self.assertNotIn('Value', metadata['00080090'])
        self.assertEqual(metadata['00080090']['vr'], 'PN')

        self.assertHasKeys(metadata['00100010'], ('vr', 'Value'))
        self.assertEqual(metadata['00100010']['vr'], 'PN')
        self.assertIsInstance(metadata['00100010']['Value'], list)
        self.assertIn('Alphabetic', metadata['00100010']['Value'][0])
        self.assertEqual(metadata['00100010']['Value'][0]['Alphabetic'],
                         'Wes Turner')

        self.assertHasKeys(metadata['00100020'], ('vr', 'Value'))
        self.assertEqual(metadata['00100020']['vr'], 'LO')
        self.assertEqual(metadata['00100020']['Value'], ['1111'])

        self.assertIn('vr', metadata['00100030'])
        self.assertNotIn('Value', metadata['00100030'])
        self.assertEqual(metadata['00100030']['vr'], 'DA')

        self.assertHasKeys(metadata['00100040'], ('vr', 'Value'))
        self.assertEqual(metadata['00100040']['vr'], 'CS')
        self.assertEqual(metadata['00100040']['Value'], ['O'])

        self.assertHasKeys(metadata['0020000D'], ('vr', 'Value'))
        self.assertEqual(metadata['0020000D']['vr'], 'UI')
        self.assertEqual(
            metadata['0020000D']['Value'],
            ['1.2.840.113619.2.133.1762890640.1886.1055165015.961'])

        self.assertHasKeys(metadata['00200010'], ('vr', 'Value'))
        self.assertEqual(metadata['00200010']['vr'], 'SH')
        self.assertEqual(metadata['00200010']['Value'], ['361'])

        # Check derived data elements

        self.assertHasKeys(metadata['00201206'], ('vr', 'Value'))
        self.assertEqual(metadata['00201206']['vr'], 'IS')
        self.assertEqual(metadata['00201206']['Value'], [1])

        self.assertHasKeys(metadata['00201208'], ('vr', 'Value'))
        self.assertEqual(metadata['00201208']['vr'], 'IS')
        self.assertEqual(metadata['00201208']['Value'], [1])

        self.assertHasKeys(metadata['00080061'], ('vr', 'Value'))
        self.assertEqual(metadata['00080061']['vr'], 'CS')
        self.assertEqual(metadata['00080061']['Value'], ['MR'])

    def testDICOMHandlerInvalid(self):
        # Upload non-DICOM data
        data = b'data'
        with EventHelper('dicom.handler.ignore') as helper:
            dcmFile = self.model('upload').uploadFromFile(
                obj=six.BytesIO(data),
                size=len(data),
                name='data',
                parentType='folder',
                parent=self.publicFolder,
                user=self.user
            )
            self.assertIsNotNone(dcmFile)

            # Wait for handler ignore event
            handled = helper.wait()
            self.assertTrue(handled)
