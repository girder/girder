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

import json
import six
import unittest

from dicom.dataelem import DataElement
from dicom.dataset import Dataset
from dicom.sequence import Sequence
from utils.dicom_json_conversion import dataElementToJSON, datasetToJSON


class ConversionTestCase(unittest.TestCase):
    """
    Test conversion from pydicom data structures to DICOM JSON Model Object
    structure.

    See: F.2.2 DICOM JSON Model Object Structure

    DataElement conversion tests cover the DICOM VRs in Table F.2.3-1,
    except for the binary VRs: OB, OD, OF, OW, UN.
    """
    def testNullDataElements(self):
        """
        F.2.5 DICOM JSON Model Null Values:

            If an attribute is present in DICOM but empty (i.e., Value Length is
            0), it shall be preserved in the DICOM JSON attribute object
            containing no "Value", "BulkDataURI" or "InlineBinary".
        """
        result = dataElementToJSON(
            DataElement((0x0010, 0x0020), 'LO', ''))
        self.assertEqual(
            result,
            {
                '00100020': {
                    'vr': 'LO'
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', ''))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS'
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x1160), 'IS', ''))
        self.assertEqual(
            result,
            {
                '00081160': {
                    'vr': 'IS'
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x1050), 'PN', ''))
        self.assertEqual(
            result,
            {
                '00081050': {
                    'vr': 'PN'
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence()))
        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ'
                }
            })

    def testNullMultiValuedDataElements(self):
        """
        F.2.5 DICOM JSON Model Null Values:

            If a multi-valued attribute has one or more empty values these are
            represented as "null" array elements.
        """
        result = dataElementToJSON(
            DataElement((0x0008, 0x0005), 'CS', r'\ISO_IR 100\ISO_IR 192'))
        self.assertEqual(
            result,
            {
                '00080005': {
                    'vr': 'CS',
                    'Value': [None, 'ISO_IR 100', 'ISO_IR 192']
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x0005), 'CS', r'ISO_IR 100\\ISO_IR 192'))
        self.assertEqual(
            result,
            {
                '00080005': {
                    'vr': 'CS',
                    'Value': ['ISO_IR 100', None, 'ISO_IR 192']
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', r'\946.746001\\-33.01'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [None, 946.746001, None, -33.01]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', r'946.746001\\-33.01'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [946.746001, None, -33.01]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', '946.746001\\-33.01\\'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [946.746001, -33.01, None]
                }
            })

    def testDataElementsToString(self):
        """
        Test conversion for data elements that map to strings.
        """
        result = dataElementToJSON(
            DataElement((0x2100, 0x0070), 'AE', 'Abcdefg'))
        self.assertEqual(
            result,
            {
                '21000070': {
                    'vr': 'AE',
                    'Value': ['Abcdefg']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0010, 0x1010), 'AS', '018M'))
        self.assertEqual(
            result,
            {
                '00101010': {
                    'vr': 'AS',
                    'Value': ['018M']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0020, 0x5000), 'AT', '00100010'))
        self.assertEqual(
            result,
            {
                '00205000': {
                    'vr': 'AT',
                    'Value': ['00100010']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0005), 'CS', 'ISO_IR 100'))
        self.assertEqual(
            result,
            {
                '00080005': {
                    'vr': 'CS',
                    'Value': ['ISO_IR 100']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0005), 'CS', r'ISO_IR 100\ISO_IR 192'))
        self.assertEqual(
            result,
            {
                '00080005': {
                    'vr': 'CS',
                    'Value': ['ISO_IR 100', 'ISO_IR 192']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0010, 0x0030), 'DA', '19930822'))
        self.assertEqual(
            result,
            {
                '00100030': {
                    'vr': 'DA',
                    'Value': ['19930822']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x002A), 'DT', '20151025143301.120400'))
        self.assertEqual(
            result,
            {
                '0008002A': {
                    'vr': 'DT',
                    'Value': ['20151025143301.120400']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0010, 0x0020), 'LO', 'ABC-123'))
        self.assertEqual(
            result,
            {
                '00100020': {
                    'vr': 'LO',
                    'Value': ['ABC-123']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0010, 0x21B0), 'LT', 'Abc. 123.'))
        self.assertEqual(
            result,
            {
                '001021B0': {
                    'vr': 'LT',
                    'Value': ['Abc. 123.']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0010), 'SH', 'ct01'))
        self.assertEqual(
            result,
            {
                '00080010': {
                    'vr': 'SH',
                    'Value': ['ct01']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0018, 0x9185), 'ST', 'Abcdefg'))
        self.assertEqual(
            result,
            {
                '00189185': {
                    'vr': 'ST',
                    'Value': ['Abcdefg']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0013), 'TM', '140130.103997'))
        self.assertEqual(
            result,
            {
                '00080013': {
                    'vr': 'TM',
                    'Value': ['140130.103997']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0119), 'UC', 'Abcdefghi'))
        self.assertEqual(
            result,
            {
                '00080119': {
                    'vr': 'UC',
                    'Value': ['Abcdefghi']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x001A), 'UI',
                        r'123.4567.012345\123.0788.44901'))
        self.assertEqual(
            result,
            {
                '0008001A': {
                    'vr': 'UI',
                    'Value': ['123.4567.012345', '123.0788.44901']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1190), 'UR', 'http://wado.nema.org/'
                        'studies/1.2.392.200036.9116.2.2.2.1762893313.'
                        '1029997326.945873'))
        self.assertEqual(
            result,
            {
                '00081190': {
                    'vr': 'UR',
                    'Value': [
                        'http://wado.nema.org/studies/'
                        '1.2.392.200036.9116.2.2.2.1762893313.'
                        '1029997326.945873']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

        result = dataElementToJSON(
            DataElement((0x0010, 0x0218), 'UT', 'Abc def ghi'))
        self.assertEqual(
            result,
            {
                '00100218': {
                    'vr': 'UT',
                    'Value': ['Abc def ghi']
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0],
                              six.string_types)

    def testDataElementsToNumber(self):
        """
        Test conversion for data elements that map to numbers.
        """
        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', '0.0'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [0.0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', '946.746001'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [946.746001]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', '-946.746001'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [-946.746001]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0008, 0x2130), 'DS', r'946.746001\1024.76\-33.01'))
        self.assertEqual(
            result,
            {
                '00082130': {
                    'vr': 'DS',
                    'Value': [946.746001, 1024.76, -33.01]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)
        self.assertIsInstance(result[list(result)[0]]['Value'][1], float)
        self.assertIsInstance(result[list(result)[0]]['Value'][2], float)

        result = dataElementToJSON(
            DataElement((0x0018, 0x1320), 'FL', '0.0'))
        self.assertEqual(
            result,
            {
                '00181320': {
                    'vr': 'FL',
                    'Value': [0.0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0018, 0x1320), 'FL', '0.625'))
        self.assertEqual(
            result,
            {
                '00181320': {
                    'vr': 'FL',
                    'Value': [0.625]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0018, 0x6028), 'FD', '0.0'))
        self.assertEqual(
            result,
            {
                '00186028': {
                    'vr': 'FD',
                    'Value': [0.0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0018, 0x6028), 'FD', '0.625'))
        self.assertEqual(
            result,
            {
                '00186028': {
                    'vr': 'FD',
                    'Value': [0.625]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], float)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1160), 'IS', '0'))
        self.assertEqual(
            result,
            {
                '00081160': {
                    'vr': 'IS',
                    'Value': [0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1160), 'IS', '30'))
        self.assertEqual(
            result,
            {
                '00081160': {
                    'vr': 'IS',
                    'Value': [30]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1160), 'IS', '-30'))
        self.assertEqual(
            result,
            {
                '00081160': {
                    'vr': 'IS',
                    'Value': [-30]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1160), 'IS', r'30\31\32\33\34'))
        self.assertEqual(
            result,
            {
                '00081160': {
                    'vr': 'IS',
                    'Value': [30, 31, 32, 33, 34]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)
        self.assertIsInstance(result[list(result)[0]]['Value'][1], int)
        self.assertIsInstance(result[list(result)[0]]['Value'][2], int)
        self.assertIsInstance(result[list(result)[0]]['Value'][3], int)
        self.assertIsInstance(result[list(result)[0]]['Value'][4], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x6020), 'SL', '0'))
        self.assertEqual(
            result,
            {
                '00186020': {
                    'vr': 'SL',
                    'Value': [0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x6020), 'SL', '1024768'))
        self.assertEqual(
            result,
            {
                '00186020': {
                    'vr': 'SL',
                    'Value': [1024768]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x6020), 'SL', '-1024768'))
        self.assertEqual(
            result,
            {
                '00186020': {
                    'vr': 'SL',
                    'Value': [-1024768]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x9219), 'SS', '0'))
        self.assertEqual(
            result,
            {
                '00189219': {
                    'vr': 'SS',
                    'Value': [0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x9219), 'SS', '1234'))
        self.assertEqual(
            result,
            {
                '00189219': {
                    'vr': 'SS',
                    'Value': [1234]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0018, 0x9219), 'SS', '-1234'))
        self.assertEqual(
            result,
            {
                '00189219': {
                    'vr': 'SS',
                    'Value': [-1234]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1161), 'UL', '0'))
        self.assertEqual(
            result,
            {
                '00081161': {
                    'vr': 'UL',
                    'Value': [0]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x1161), 'UL', '5002343'))
        self.assertEqual(
            result,
            {
                '00081161': {
                    'vr': 'UL',
                    'Value': [5002343]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

        result = dataElementToJSON(
            DataElement((0x0008, 0x0040), 'US', '1234'))
        self.assertEqual(
            result,
            {
                '00080040': {
                    'vr': 'US',
                    'Value': [1234]
                }
            })
        self.assertIsInstance(result[list(result)[0]]['Value'][0], int)

    def testPersonNameDataElement(self):
        """
        Test conversion for Person Name data element to Object containing name
        components as strings.

        F.2.2 DICOM JSON Model Object Structure:

            The non-empty name components of each element are encoded as a JSON
            strings with the following names:

            - Alphabetic
            - Ideographic
            - Phonetic

        """
        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', 'Adams^John Robert Quincy^^'
                                                'Rev.^B.A. M.Div.'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            'Adams^John Robert Quincy^^'
                            'Rev.^B.A. M.Div.'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', 'Morrison-Jones^Susan^^^'
                                                'Ph.D., Chief Executive '
                                                'Officer'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            'Morrison-Jones^Susan^^^'
                            'Ph.D., Chief Executive Officer'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', '=A^B^^'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Ideographic':
                            'A^B^^'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', '==A^B^^'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Phonetic':
                            'A^B^^'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', 'A^B=C^D'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            'A^B',
                            'Ideographic':
                            'C^D'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', 'A^B==C^D'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            'A^B',
                            'Phonetic':
                            'C^D'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', 'A^B=C^D=E^F'))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            'A^B',
                            'Ideographic':
                            'C^D',
                            'Phonetic':
                            'E^F'
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x0010), 'PN', '=='))
        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN'
                }
            })

    def testSequenceDataElement(self):
        """
        Test conversion for Sequence data element to Array containing DICOM JSON
        Objects.

        F.2.5 DICOM JSON Model Null Values:

            If a sequence contains empty items these are represented as empty
            JSON objects in the array.

        """
        ds0 = Dataset()  # Empty dataset

        ds1 = Dataset()
        ds1.add_new((0x0010, 0x0010), 'PN', '^Bob^^Mrs.')
        ds1.add_new((0x0010, 0x0020), 'LO', '41033')
        ds1.add_new((0x0010, 0x0021), 'LO', 'Hospital A')

        ds2 = Dataset()
        ds2.add_new((0x0010, 0x0010), 'PN', '^Bob^^Mr.')
        ds2.add_new((0x0010, 0x0020), 'LO', '981811')
        ds2.add_new((0x0010, 0x0021), 'LO', 'Hospital B')

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence((ds1,))))

        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mrs.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['41033']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital A']
                            }
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence((ds1, ds2))))
        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mrs.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['41033']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital A']
                            }
                        },
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mr.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['981811']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital B']
                            }
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence((ds0, ds2))))
        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                        },
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mr.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['981811']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital B']
                            }
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence((ds1, ds0))))
        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mrs.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['41033']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital A']
                            }
                        },
                        {
                        }
                    ]
                }
            })

        result = dataElementToJSON(
            DataElement((0x0010, 0x1002), 'SQ', Sequence((ds1, ds0, ds2))))
        self.assertEqual(
            result,
            {
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mrs.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['41033']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital A']
                            }
                        },
                        {
                        },
                        {
                            '00100010': {
                                'vr': 'PN',
                                'Value': [
                                    {
                                        'Alphabetic':
                                        '^Bob^^Mr.'
                                    }
                                ]
                            },
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['981811']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital B']
                            }
                        }
                    ]
                }
            })

    def testDatasetToJSON(self):
        """
        Test conversion of dataset to DICOM JSON Object.
        """
        ds = Dataset()
        ds.add_new((0x0008, 0x0008), 'CS', ['ORIGINAL', 'PRIMARY', 'LOCALIZER'])
        ds.add_new((0x0008, 0x0018), 'UI', '1.2.840.113770.2.1.2915483100.'
                                           '2110896889.4098778746')
        ds.add_new((0x0008, 0x0020), 'DA', '20110823')
        ds.add_new((0x0010, 0x0010), 'PN', '^Bob^^Dr.')
        ds.add_new((0x0010, 0x0020), 'LO', '515469237')
        ds.add_new((0x0010, 0x0021), 'LO', 'Hospital A')
        ds.add_new((0x0010, 0x0030), 'DA', '')
        ds.add_new((0x0010, 0x0040), 'CS', 'M')
        ds.add_new((0x0010, 0x0050), 'DS', '3.0000000')
        ds.add_new((0x0020, 0x0010), 'SH', '3')
        ds.add_new((0x0020, 0x0011), 'IS', '1')
        ds.add_new((0x0020, 0x0012), 'IS', '0')
        ds.add_new((0x0020, 0x0013), 'IS', '0')
        ds.add_new((0x0028, 0x0030), 'DS', r'2.0\2.0')

        ds1 = Dataset()
        ds1.add_new((0x0010, 0x0020), 'LO', '41033')
        ds1.add_new((0x0010, 0x0021), 'LO', 'Hospital B')
        ds2 = Dataset()
        ds2.add_new((0x0010, 0x0020), 'LO', '981811')
        ds2.add_new((0x0010, 0x0021), 'LO', 'Hospital C')
        ds.add_new((0x0010, 0x1002), 'SQ', Sequence((ds1, ds2)))

        result = datasetToJSON(ds)

        self.assertEqual(
            result,
            {
                '00080008': {
                    'vr': 'CS',
                    'Value': ['ORIGINAL', 'PRIMARY', 'LOCALIZER']
                },
                '00080018': {
                    'vr': 'UI',
                    'Value': ['1.2.840.113770.2.1.2915483100.'
                              '2110896889.4098778746']
                },
                '00080020': {
                    'vr': 'DA',
                    'Value': ['20110823']
                },
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic':
                            '^Bob^^Dr.'
                        }
                    ]
                },
                '00100020': {
                    'vr': 'LO',
                    'Value': ['515469237']
                },
                '00100021': {
                    'vr': 'LO',
                    'Value': ['Hospital A']
                },
                '00100030': {
                    'vr': 'DA'
                },
                '00100040': {
                    'vr': 'CS',
                    'Value': ['M']
                },
                '00100050': {
                    'vr': 'DS',
                    'Value': [3.0000000]
                },
                '00200010': {
                    'vr': 'SH',
                    'Value': ['3']
                },
                '00200011': {
                    'vr': 'IS',
                    'Value': [1]
                },
                '00200012': {
                    'vr': 'IS',
                    'Value': [0]
                },
                '00200013': {
                    'vr': 'IS',
                    'Value': [0]
                },
                '00280030': {
                    'vr': 'DS',
                    'Value': [2.0, 2.0]
                },
                '00101002': {
                    'vr': 'SQ',
                    'Value': [
                        {
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['41033']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital B']
                            }
                        },
                        {
                            '00100020': {
                                'vr': 'LO',
                                'Value': ['981811']
                            },
                            '00100021': {
                                'vr': 'LO',
                                'Value': ['Hospital C']
                            }
                        }
                    ]
                }
            })

        # Serialize to JSON-formatted string
        s = json.dumps(result)

    def testUnicodeDatasetToJSON(self):
        """
        Test conversion of dataset with Unicode values to DICOM JSON Object.
        """
        ds = Dataset()
        ds.add_new((0x0010, 0x0010), 'PN', 'Wang^XiaoDong=王^小東')
        ds.add_new((0x0010, 0x0021), 'LO', '王小東小東')

        result = datasetToJSON(ds)

        self.assertEqual(
            result,
            {
                '00100010': {
                    'vr': 'PN',
                    'Value': [
                        {
                            'Alphabetic': 'Wang^XiaoDong',
                            'Ideographic': '王^小東'
                        }
                    ]
                },
                '00100021': {
                    'vr': 'LO',
                    'Value': ['王小東小東']
                }
            })

        # Serialize to JSON-formatted string
        s = json.dumps(result)
