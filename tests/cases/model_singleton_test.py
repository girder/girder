#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2017 Kitware Inc.
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

import mock
import unittest

from girder.models.item import Item


class ModelSingletonTest(unittest.TestCase):
    @mock.patch.object(Item, '__init__', return_value=None)
    def testModelSingletonBehavior(self, initMock):
        self.assertEqual(len(initMock.mock_calls), 0)
        Item()
        Item()
        self.assertEqual(len(initMock.mock_calls), 1)

        # Make sure it works for subclasses of other models
        class Subclass(Item):
            pass

        with mock.patch.object(Subclass, '__init__', return_value=None) as patch:
            self.assertEqual(len(patch.mock_calls), 0)
            Subclass()
            Subclass()
            self.assertEqual(len(patch.mock_calls), 1)
