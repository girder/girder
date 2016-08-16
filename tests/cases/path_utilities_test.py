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
from girder.utility import path

strings = [
    ('abcd', 'abcd'),
    ('/', '\/'),
    ('\\', '\\\\'),
    ('/\\', '\/\\\\'),
    ('\\//\\', '\\\\\/\/\\\\'),
    ('a\\\\b//c\\d', 'a\\\\\\\\b\/\/c\\\\d')
]

paths = [
    ('abcd', ['abcd']),
    ('/abcd', ['', 'abcd']),
    ('/ab/cd/ef/gh', ['', 'ab', 'cd', 'ef', 'gh']),
    ('/ab/cd//', ['', 'ab', 'cd', '', '']),
    ('ab\\/cd', ['ab/cd']),
    ('ab\/c/d', ['ab/c', 'd']),
    ('ab\//cd', ['ab/', 'cd']),
    ('ab/\/cd', ['ab', '/cd']),
    ('ab\\\\/cd', ['ab\\', 'cd']),
    ('ab\\\\/\\\\cd', ['ab\\', '\\cd']),
    ('ab\\\\\\/\\\\cd', ['ab\\/\\cd']),
    ('/\\\\abcd\\\\/', ['', '\\abcd\\', '']),
    ('/\\\\\\\\/\\//\\\\', ['', '\\\\', '/', '\\'])
]


class TestPathUtilities(unittest.TestCase):
    """Tests the girder.utility.path module."""

    def testEncodeStrings(self):
        for raw, encoded in strings:
            self.assertEqual(path.encode(raw), encoded)

    def testDecodeStrings(self):
        for raw, encoded in strings:
            self.assertEqual(path.decode(encoded), raw)

    def testSplitPath(self):
        for pth, tokens in paths:
            self.assertEqual(path.split(pth), tokens)

    def testJoinTokens(self):
        for pth, tokens in paths:
            self.assertEqual(path.join(tokens), pth)
