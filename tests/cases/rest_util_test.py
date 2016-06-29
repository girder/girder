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

import datetime
import json
import pytz
import six
import unittest

from girder.api import rest
import girder.events

date = datetime.datetime.now()


class TestResource(object):
    @rest.endpoint
    def returnsSet(self, *args, **kwargs):
        return {'key': {1, 2, 3}}

    @rest.endpoint
    def returnsDate(self, *args, **kwargs):
        return {'key': date}

    @rest.endpoint
    def returnsInf(self, *args, **kwargs):
        return {'value': float('inf')}


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

        for input, output in six.viewitems(expect):
            params = {
                'some_key': input
            }
            self.assertEqual(resource.boolParam('some_key', params), output)

        self.assertEqual(resource.boolParam('some_key', {}, default='x'), 'x')

    def testGetApiUrl(self):
        url = 'https://localhost/thing/api/v1/hello/world?foo=bar#test'
        self.assertEqual(rest.getApiUrl(url), 'https://localhost/thing/api/v1')

        parts = rest.getUrlParts(url)
        self.assertEqual(parts.path, '/thing/api/v1/hello/world')
        self.assertEqual(rest.getApiUrl(parts.path), '/thing/api/v1')
        self.assertEqual(parts.port, None)
        self.assertEqual(parts.hostname, 'localhost')
        self.assertEqual(parts.query, 'foo=bar')
        self.assertEqual(parts.fragment, 'test')

        url = 'https://localhost/girder#users'
        self.assertRaises(Exception, rest.getApiUrl, url=url)

    def testCustomJsonEncoder(self):
        resource = TestResource()
        resp = resource.returnsSet().decode('utf8')
        self.assertEqual(json.loads(resp), {'key': [1, 2, 3]})

        resp = resource.returnsDate().decode('utf8')
        self.assertEqual(json.loads(resp), {
            'key': date.replace(tzinfo=pytz.UTC).isoformat()
        })

        # Returning infinity or NaN floats should raise a reasonable exception
        regex = 'Out of range float values are not JSON compliant'
        with six.assertRaisesRegex(self, ValueError, regex):
            resp = resource.returnsInf()

    def testCustomJsonEncoderEvent(self):
        def _toString(event):
            obj = event.info
            if isinstance(obj, set):
                event.addResponse(str(list(obj)))

        with girder.events.bound('rest.json_encode', 'toString', _toString):
            resource = TestResource()
            resp = resource.returnsSet().decode('utf8')
            self.assertEqual(json.loads(resp), {'key': '[1, 2, 3]'})
            # Check we still get default encode for date
            resp = resource.returnsDate().decode('utf8')
            self.assertEqual(json.loads(resp), {
                'key': date.replace(tzinfo=pytz.UTC).isoformat()
            })
