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

import unittest

from girder.api import rest


class RestUtilTestCase(unittest.TestCase):
    """
    This performs unit-level testing of REST-related utilities.
    """

    def testBoolParam(self):
        resource = rest.Resource()
        expect = {
            'TRUE': True,
            ' true  ': True,
            'Yes': True,
            '1': True,
            'ON': True,
            'false': False,
            'False': False,
            'OFF': False,
            '': False,
            ' ': False,
            False: False,
            True: True
        }

        for input, output in expect.items():
            params = {
                'some_key': input
            }
            self.assertEqual(resource.boolParam('some_key', params), output)

        self.assertEqual(resource.boolParam('some_key', {}, default='x'), 'x')
