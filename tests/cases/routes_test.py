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

from girder.api.rest import Resource, RestException


class DummyResource(Resource):
    def __init__(self):
        self.resourceName = 'foo'
        self.route('GET', (':wc1', 'literal1'), self.handler)
        self.route('GET', (':wc1', 'literal2'), self.handler)
        self.route('GET', (':wc1', ':wc2'), self.handler)
        self.route('GET', (':wc1', 'literal1'), self.handler)
        self.route('GET', ('literal1', 'literal2'), self.handler)
        self.route('GET', (':wc1', 'admin'), self.handler)

    def handler(self, **kwargs):
        return kwargs


class RoutesTestCase(unittest.TestCase):
    """
    Unit tests of the routing system of REST Resources.
    """
    def testRouteSystem(self):
        dummy = DummyResource()

        # Bad route should give a useful exception.
        exc = None
        try:
            r = dummy.handleRoute('GET', (), {})
        except RestException as e:
            exc = e.message
        self.assertEqual(exc, 'No matching route for "GET "')

        # Make sure route ordering is correct; literals before wildcard tokens
        r = dummy.handleRoute('GET', ('literal1', 'foo'), {})
        self.assertEqual(r, {'wc1': 'literal1', 'wc2': 'foo', 'params': {}})

        r = dummy.handleRoute('GET', ('literal1', 'literal2'), {})
        self.assertEqual(r, {'params': {}})
