# -*- coding: utf-8 -*-
import unittest
import unittest.mock

from girder.models.item import Item


class ModelSingletonTest(unittest.TestCase):
    @unittest.mock.patch.object(Item, '__init__', return_value=None)
    def testModelSingletonBehavior(self, initMock):
        self.assertEqual(len(initMock.mock_calls), 0)
        Item()
        Item()
        self.assertEqual(len(initMock.mock_calls), 1)

        # Make sure it works for subclasses of other models
        class Subclass(Item):
            pass

        with unittest.mock.patch.object(Subclass, '__init__', return_value=None) as patch:
            self.assertEqual(len(patch.mock_calls), 0)
            Subclass()
            Subclass()
            self.assertEqual(len(patch.mock_calls), 1)
