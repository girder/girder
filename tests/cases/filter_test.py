#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
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

from .. import base
from girder.models.model_base import AccessControlledModel, Model, AccessType
from girder.utility.model_importer import ModelImporter


class FakeAcModel(AccessControlledModel):
    def initialize(self):
        self.name = 'fake_ac'

        self.exposeFields(level=AccessType.READ, fields='read')
        self.exposeFields(level=AccessType.WRITE, fields=('write', 'write2'))
        self.exposeFields(level=AccessType.ADMIN, fields='admin')
        self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

    def validate(self, doc):
        return doc


class FakeModel(Model):
    def initialize(self):
        self.name = 'fake'

        self.exposeFields(level=AccessType.READ, fields='read')
        self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

    def validate(self, doc):
        return doc


def setUpModule():
    base.startServer()


def tearDownModule():
    base.stopServer()


class FilterTestCase(base.TestCase):
    """
    Unit test the model filtering utilities.
    """
    def setUp(self):
        base.TestCase.setUp(self)

        users = ({
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }, {
            'email': 'regularuser@email.com',
            'login': 'regularuser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        })
        self.admin, self.user = [
            self.model('user').createUser(**user) for user in users]

        ModelImporter.registerModel('fake_ac', FakeAcModel())
        ModelImporter.registerModel('fake', FakeModel())

    def testModelFiltering(self):
        fields = {
            'hidden': 1,
            'read': 1,
            'write': 1,
            'write2': 1,
            'admin': 1,
            'sa': 1
        }

        # Test filter behavior on access controlled model
        fakeAc = self.model('fake_ac').save(fields)
        fakeAc = self.model('fake_ac').setUserAccess(
            fakeAc, self.user, level=AccessType.READ)

        filtered = self.model('fake_ac').filter(fakeAc, self.admin)
        self.assertTrue('sa' in filtered)
        self.assertTrue('write' in filtered)
        self.assertFalse('hidden' in filtered)

        self.model('fake_ac').exposeFields(
            level=AccessType.READ, fields='hidden')

        filtered = self.model('fake_ac').filter(fakeAc, self.user)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('read' in filtered)
        self.assertFalse('write' in filtered)
        self.assertFalse('admin' in filtered)
        self.assertFalse('sa' in filtered)

        self.model('fake_ac').hideFields(level=AccessType.READ, fields='read')

        fakeAc = self.model('fake_ac').setUserAccess(
            fakeAc, self.user, level=AccessType.ADMIN)

        filtered = self.model('fake_ac').filter(fakeAc, self.user)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('write' in filtered)
        self.assertTrue('admin' in filtered)
        self.assertFalse('read' in filtered)
        self.assertFalse('sa' in filtered)

        # Test Model implementation
        fake = self.model('fake').save(fields)
        filtered = self.model('fake').filter(fake, self.user)
        self.assertEqual(filtered, {'read': 1, '_modelType': 'fake'})

        filtered = self.model('fake').filter(fake, self.admin)
        self.assertEqual(filtered, {
            'read': 1,
            'sa': 1,
            '_modelType': 'fake'
        })
