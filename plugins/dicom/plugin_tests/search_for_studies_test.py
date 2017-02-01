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
import unittest
from tests import base
from utils.event_helper import EventHelper


def setUpModule():
    base.enabledPlugins.append('dicom')
    base.startServer()


def tearDownModule():
    base.stopServer()


class SearchForStudiesTestCase(base.TestCase):
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

        files = [
            'Image0075.dcm',
            'Image0076.dcm',
            'Image0077.dcm',
            '012345.002.050',
            '9575',
            '9605',
            '9635',
            '9665'
        ]

        for filename in files:
            dcmFilePath = os.path.join(
                os.environ['GIRDER_TEST_DATA_PREFIX'],
                'plugins',
                'dicom',
                filename
            )
            self.assertTrue(os.path.exists(dcmFilePath))

            # Upload the dicom file
            dcmData = None
            with open(dcmFilePath, 'rb') as f:
                dcmData = f.read()
            self.assertTrue(dcmData)

            with EventHelper('dicom.handler.success') as helper:
                dcmFile = self.model('upload').uploadFromFile(
                    obj=six.BytesIO(dcmData),
                    size=len(dcmData),
                    name=filename,
                    parentType='folder',
                    parent=self.publicFolder,
                    user=self.user,
                    mimeType='application/dicom'
                )
                self.assertIsNotNone(dcmFile)

                # Wait for handler success event
                handled = helper.wait()
                self.assertTrue(handled)

    def tearDown(self):
        base.TestCase.tearDown(self)

        # Remove user
        self.model('user').remove(self.user)

    def testSupportedQueryKeys(self):
        """
        Test SearchForStudies supported query keys.

        See 6.7.1.2.1.1 Study Matching.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'StudyDate': '20030625'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'StudyTime': '152734'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'AccessionNumber': ''
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'ModalitiesInStudy': 'MR'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'ReferringPhysicianName': ''
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientName': 'Wes Turner'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)

        resp = self.request(path='/studies', user=self.user, params={
            'StudyID': '361'
        })
        self.assertStatusOk(resp)

    def testDuplicateQueryKeys(self):
        """
        Test SearchForStudies with duplicate query keys.

        See 6.7.1.1.1 {attributeID} encoding rules.
        """
        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyDate', '20030625'),
            ('StudyDate', '20030625')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00080020', '20030625'),
            ('00080020', '20030625')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyDate', '20030625'),
            ('00080020', '20030625')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyTime', '152734'),
            ('StudyTime', '152734')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00080030', '152734'),
            ('00080030', '152734')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyTime', '152734'),
            ('00080030', '152734')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('AccessionNumber', ''),
            ('AccessionNumber', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00080050', ''),
            ('00080050', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('AccessionNumber', ''),
            ('00080050', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('ModalitiesInStudy', ''),
            ('ModalitiesInStudy', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00080061', ''),
            ('00080061', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('ModalitiesInStudy', ''),
            ('00080061', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('ReferringPhysicianName', ''),
            ('ReferringPhysicianName', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00080090', ''),
            ('00080090', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('ReferringPhysicianName', ''),
            ('00080090', '')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientName', 'Wes Turner'),
            ('PatientName', 'Wes Turner')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00100010', 'Wes Turner'),
            ('00100010', 'Wes Turner')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientName', 'Wes Turner'),
            ('00100010', 'Wes Turner')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('PatientID', '1111')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00100020', '1111'),
            ('00100020', '1111')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('00100020', '1111')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyInstanceUID',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'),
            ('StudyInstanceUID',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('0020000D',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'),
            ('0020000D',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyInstanceUID',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'),
            ('0020000D',
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyID', '361'),
            ('StudyID', '361')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('00200010', '361'),
            ('00200010', '361')
        ])
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params=[
            ('StudyID', '361'),
            ('00200010', '361')
        ])
        self.assertStatus(resp, 400)

    def testUnsupportedQueryKeys(self):
        """
        Test SearchForStudies with unsupported query keys.

        See 6.7.1.2.1.1 Study Matching.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'Modality': ''
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            '00080060': ''
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'Manufacturer': ''
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            '00080070': ''
        })
        self.assertStatus(resp, 400)

    def testSingleValueMatching(self):
        """
        Test single value matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        resp = self.request(path='/studies', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            '00100020': '1111'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            '0020000D':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': 'XX-XXXXX'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            '00100020': 'XX-XXXXX'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            '00100020': '2222'
        }, isJson=False)
        self.assertStatus(resp, 204)
        self.assertEqual(len(self.getBody(resp)), 0)

        # TODO add more

        # TODO add tests for date/time tags
        # See: C.2.2.2.1 Single Value Matching

        # TODO add more tests for PN tags
        # See: C.2.2.2.1 Single Value Matching

        resp = self.request(path='/studies', user=self.user, params={
            'PatientName': 'Wes Turner'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientName': 'Doe^Peter'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            'ModalitiesInStudy': 'MR'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/studies', user=self.user, params={
            'ModalitiesInStudy': 'CT'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

    @unittest.skip('not implemented')
    def testListOfUIDMatching(self):
        """
        Test list of UID matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        self.fail('not implemented')

    @unittest.skip('not implemented')
    def testUniversalMatching(self):
        """
        Test universal matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        self.fail('not implemented')

    @unittest.skip('not implemented')
    def testWildCardMatching(self):
        """
        Test wild card matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        self.fail('not implemented')

    @unittest.skip('not implemented')
    def testRangeMatching(self):
        """
        Test range matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        self.fail('not implemented')

    @unittest.skip('not implemented')
    def testSequenceMatching(self):
        """
        Test matching on query keys.

        See 6.7.1.2.1 Matching / C.2.2.2 Attribute Matching
        """
        self.fail('not implemented')

    def testReturnedAttributes(self):
        """
        Test study result attributes.

        See 6.7.1.2.2.1 Study Result Attributes
        """
        # XXX: derived attributes
        expectedKeys = [
            '00080005',  # Specific Character Set
            '00080020',  # Study Date
            '00080030',  # Study Time
            '00080050',  # Accession Number
            '00080056',  # Instance Availability
            '00080061',  # Modalities in Study
            '00080090',  # Referring Physician's Name
            # '00080201',  # Timezone Offset From UTC
            '00081190',  # Retrieve URL
            '00100010',  # Patient's Name
            '00100020',  # Patient ID
            '00100030',  # Patient's Birth Date
            '00100040',  # Patient's Sex
            '0020000D',  # Study Instance UID
            '00200010',  # Study ID
            '00201206',  # Number of Study Related Series
            '00201208'   # Number of Study Related Instances
        ]

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertHasKeys(resp.json[0], expectedKeys)
        self.assertEqual(len(resp.json[0]), 16)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': 'XX-XXXXX'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertHasKeys(resp.json[0], expectedKeys)
        self.assertEqual(len(resp.json[0]), 16)

    def testIncludeField(self):
        """
        Test includefield / {attributeID} pairs in query.

        See: 6.7.1 QIDO-RS - Search
        """
        # Test single includefield / {attributeID} pair
        #
        # Expected to return all attributes expected in
        # testReturnedAttributes(), plus the additional requested attribute.

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': 'InstitutionName'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertEqual(len(resp.json[0]), 17)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': '00080080'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertEqual(len(resp.json[0]), 17)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': 'InstanceNumber'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 17)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': '00200013'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 17)

        # Test multiple includefield / {attributeID} pairs
        #
        # Expected to return all attributes expected in
        # testReturnedAttributes(), plus the additional requested attributes.

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('includefield', 'InstitutionName'),
            ('includefield', 'InstanceNumber')
        ])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 18)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('includefield', '00080080'),
            ('includefield', 'InstanceNumber')
        ])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 18)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('includefield', 'InstitutionName'),
            ('includefield', '00200013')
        ])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 18)

        resp = self.request(path='/studies', user=self.user, params=[
            ('PatientID', '1111'),
            ('includefield', '00080080'),
            ('includefield', '00200013')
        ])
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080080', resp.json[0])
        self.assertIn('00200013', resp.json[0])
        self.assertEqual(len(resp.json[0]), 18)

    # TODO
    @unittest.skip('not implemented')
    def testIncludeFieldElementOfSequence(self):
        """
        See: 6.7.1.1.1 {attributeID} encoding rules:

            {attributeID} can be one of the following:

            [...]

            {dicomTag}.{attributeID}, where {attributeID} is an element of the
            sequence specified by {dicomTag}

            {dicomKeyword}.{attributeID}, where {attributeID} is an element of
            the sequence specified by {dicomKeyword}
        """
        self.fail()

    # TODO
    @unittest.skip('not implemented')
    def testIncludeFieldAll(self):
        """
        See: Table 6.7.1-2. QIDO-RS STUDY Returned Attributes
        """
        # Test includefield=all
        #
        # See: Table 6.7.1-2. QIDO-RS STUDY Returned Attributes
        #
        # All available Study Level DICOM Attributes if the "includefield" query
        # key is included with a value of "all"

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': 'all'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        # TODO should include only study level attributes
        # self.assertEqual(len(resp.json[0]), numStudyLevelAttributes)

        # XXX: use test data with different number of data elements
        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': 'XX-XXXXX',
            'includefield': 'all'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        # TODO should include only study level attributes
        # self.assertEqual(len(resp.json[0]), numStudyLevelAttributes)

        # Test includefield=all with other pair specified
        # TODO

        self.fail()

    def testIncludeFieldInvalid(self):
        """
        Test passing invalid input for 'includefield' values.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': 'InvalidTag'
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': '0010001020'
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': 'FFFFFFFF'
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': '0010'
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': '10'
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': ''
        })
        self.assertStatus(resp, 400)

        resp = self.request(path='/studies', user=self.user, params={
            'PatientID': '1111',
            'includefield': ' '
        })
        self.assertStatus(resp, 400)

    # TODO
    @unittest.skip('not implemented')
    def testIncludeFieldSeriesAndInstanceLevel(self):
        """
        See: 6.7.1.2.2.1 Study Result Attributes:

            Series Level and Instance Level attributes passed as "includefield"
            query values shall not be returned.
        """
        self.fail()

    def testNumberOfStudyRelatedSeries(self):
        """
        Test NumberOfStudyRelatedSeries tag.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.5.1762386977.1328.985934491.590'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201206', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201206'])
        self.assertEqual(resp.json[0]['00201206']['Value'], [1])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201206', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201206'])
        self.assertEqual(resp.json[0]['00201206']['Value'], [1])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.3.6.1.4.1.5962.1.1.0.0.0.1196533885.18148.0.133'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201206', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201206'])
        self.assertEqual(resp.json[0]['00201206']['Value'], [2])

    def testNumberOfRelatedInstances(self):
        """
        Test NumberOfStudyRelatedInstances tag.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.5.1762386977.1328.985934491.590'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201208', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201208'])
        self.assertEqual(resp.json[0]['00201208']['Value'], [1])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201208', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201208'])
        self.assertEqual(resp.json[0]['00201208']['Value'], [3])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.3.6.1.4.1.5962.1.1.0.0.0.1196533885.18148.0.133'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00201208', resp.json[0])
        self.assertIn('Value', resp.json[0]['00201208'])
        self.assertEqual(resp.json[0]['00201208']['Value'], [4])

    def testModalitiesInStudy(self):
        """
        Test ModalitiesInStudy tag.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.5.1762386977.1328.985934491.590'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080061', resp.json[0])
        self.assertIn('Value', resp.json[0]['00080061'])
        self.assertEqual(resp.json[0]['00080061']['Value'], ['MR'])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.2.840.113619.2.133.1762890640.1886.1055165015.961'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080061', resp.json[0])
        self.assertIn('Value', resp.json[0]['00080061'])
        self.assertEqual(resp.json[0]['00080061']['Value'], ['MR'])

        resp = self.request(path='/studies', user=self.user, params={
            'StudyInstanceUID':
                '1.3.6.1.4.1.5962.1.1.0.0.0.1196533885.18148.0.133'
        })
        self.assertEqual(len(resp.json), 1)
        self.assertIn('00080061', resp.json[0])
        self.assertIn('Value', resp.json[0]['00080061'])
        self.assertEqual(resp.json[0]['00080061']['Value'], ['CT', 'MR'])

    def testFuzzyMatching(self):
        """
        Test 'fuzzymatching' parameter.

        See 6.7.1.2.1 Matching.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'fuzzymatching': 'false'
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/studies', user=self.user, params={
            'fuzzymatching': 'true'
        })
        self.assertStatusOk(resp)
        self.assertIn('Warning', resp.headers)
        self.assertIn('fuzzymatching', resp.headers['Warning'])
        self.assertTrue(resp.headers['Warning'].startswith('299 '))
        self.assertEqual(len(resp.json), 3)

    def testLimit(self):
        """
        Test 'limit' parameter.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'limit': 0
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 1
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 2
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 3
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 4
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)

    def testOffset(self):
        """
        Test 'offset' parameter.
        """
        resp = self.request(path='/studies', user=self.user, params={
            'limit': 0,
            'offset': 0
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        uid0 = resp.json[0]['0020000D']['Value'][0]

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 0,
            'offset': 1
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 2)
        uid1 = resp.json[0]['0020000D']['Value'][0]
        self.assertNotEqual(uid0, uid1)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 0,
            'offset': 2
        })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        uid2 = resp.json[0]['0020000D']['Value'][0]
        self.assertNotEqual(uid0, uid1)
        self.assertNotEqual(uid0, uid2)

        resp = self.request(path='/studies', user=self.user, params={
            'limit': 0,
            'offset': 3
        }, isJson=False)
        self.assertStatus(resp, 204)
