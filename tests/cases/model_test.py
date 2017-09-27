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


class ModelTestCase(base.TestCase):
    """
    Unit test the model-related functionality and utilities.
    """
    def setUp(self):
        base.TestCase.setUp(self)

        ModelImporter.registerModel('fake_ac', FakeAcModel())
        ModelImporter.registerModel('fake', FakeModel())

    def testProjectionUtils(self):
        def assertItemsEqual(a, b):
            self.assertEqual(len(a), len(b))
            self.assertEqual(sorted(a), sorted(b))

        inclusionProjDict = {
            'public': True,
            'access': True,
            'email': True,
            'login': True
        }
        inclusionProjList = ['public', 'access', 'email', 'login']
        exclusionProjDict = {
            'public': False,
            'access': False,
            'email': False,
            'login': False
        }
        overrideFields = {'access', 'public'}

        copy = dict(inclusionProjDict)
        retval = Model._overwriteFields(inclusionProjDict, overrideFields)
        assertItemsEqual(retval, inclusionProjDict)
        assertItemsEqual(inclusionProjDict, copy)
        retval = Model._overwriteFields(inclusionProjList, overrideFields)
        assertItemsEqual(retval, inclusionProjList)
        retval = Model._overwriteFields(exclusionProjDict, {'newValue'})
        assertItemsEqual(retval, exclusionProjDict)
        retval = Model._overwriteFields(inclusionProjDict, {'newValue'})
        assertItemsEqual(retval, {
            'public': True,
            'access': True,
            'email': True,
            'login': True,
            'newValue': True
        })
        retval = Model._overwriteFields(exclusionProjDict, overrideFields)
        assertItemsEqual(retval, {'email': False, 'login': False})

        doc = {
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'
        }
        Model._removeOverwrittenFields(doc, exclusionProjDict)
        assertItemsEqual(doc, {
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'})

        doc = {
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'
        }
        Model._removeOverwrittenFields(doc, inclusionProjList)
        assertItemsEqual(doc, {
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'})

        doc = {
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'
        }
        Model._removeOverwrittenFields(doc, inclusionProjDict)
        assertItemsEqual(doc, {
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'})

        # Test None edge cases
        retval = Model._overwriteFields(None, {'access', 'public'})
        self.assertIsNone(retval)
        copy = dict(doc)
        Model._removeOverwrittenFields(doc, None)
        assertItemsEqual(copy, doc)

        # Test '_id': False inclusion edge case
        fields = {
            '_id': False,
            'login': True,
            'email': True,
            'firstName': True,
            'lastName': True
        }
        overwrittenFields = {
            '_id': True,
            'login': True,
            'email': True,
            'firstName': True,
            'lastName': True
        }
        overwrite = {'_id', 'login'}
        retval = Model._overwriteFields(fields, overwrite)
        assertItemsEqual(retval, overwrittenFields)
        doc = {
            '_id': 'id',
            'login': 'login',
            'email': 'email@email.com',
            'firstName': 'fname',
            'lastName': 'lname'
        }
        Model._removeOverwrittenFields(doc, fields)
        assertItemsEqual(doc, {
            'login': 'login',
            'email': 'email@email.com',
            'firstName': 'fname',
            'lastName': 'lname'})

        # Test _isInclusionProjection edge cases
        self.assertEqual(Model._isInclusionProjection(None), False)
        self.assertEqual(Model._isInclusionProjection({}), True)
        self.assertEqual(Model._isInclusionProjection({'_id': False}), False)
        self.assertEqual(Model._isInclusionProjection({'_id': True}), True)

    def testModelFiltering(self):
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
        adminUser, regUser = [
            self.model('user').createUser(**user) for user in users]

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
            fakeAc, regUser, level=AccessType.READ)

        filtered = self.model('fake_ac').filter(fakeAc, adminUser)
        self.assertTrue('sa' in filtered)
        self.assertTrue('write' in filtered)
        self.assertFalse('hidden' in filtered)

        self.model('fake_ac').exposeFields(
            level=AccessType.READ, fields='hidden')

        filtered = self.model('fake_ac').filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('read' in filtered)
        self.assertFalse('write' in filtered)
        self.assertFalse('admin' in filtered)
        self.assertFalse('sa' in filtered)

        self.model('fake_ac').hideFields(level=AccessType.READ, fields='read')

        fakeAc = self.model('fake_ac').setUserAccess(
            fakeAc, regUser, level=AccessType.ADMIN)

        filtered = self.model('fake_ac').filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('write' in filtered)
        self.assertTrue('admin' in filtered)
        self.assertFalse('read' in filtered)
        self.assertFalse('sa' in filtered)

        # Test Model implementation
        fake = self.model('fake').save(fields)
        filtered = self.model('fake').filter(fake, regUser)
        self.assertEqual(filtered, {'read': 1, '_modelType': 'fake'})

        filtered = self.model('fake').filter(fake, adminUser)
        self.assertEqual(filtered, {
            'read': 1,
            'sa': 1,
            '_modelType': 'fake'
        })

    def testAccessControlCleanup(self):
        # Create documents
        user1 = self.model('user').createUser(
            email='guy@place.com',
            login='someguy',
            firstName='Some',
            lastName='Guy',
            password='mypassword'
        )
        user2 = self.model('user').createUser(
            email='other@place.com',
            login='otherguy',
            firstName='Other',
            lastName='Guy',
            password='mypassword2'
        )
        group1 = self.model('group').createGroup(
            name='agroup',
            creator=user2
        )
        doc1 = {
            'creatorId': user1['_id'],
            'field1': 'value1',
            'field2': 'value2'
        }
        doc1 = self.model('fake_ac').setUserAccess(
            doc1, user1, level=AccessType.ADMIN)
        doc1 = self.model('fake_ac').setUserAccess(
            doc1, user2, level=AccessType.READ)
        doc1 = self.model('fake_ac').setGroupAccess(
            doc1, group1, level=AccessType.WRITE)
        doc1 = self.model('fake_ac').save(doc1)
        doc1Id = doc1['_id']

        # Test pre-delete
        # The raw ACL properties must be examined directly, as the
        # "getFullAccessList" method will silently remove leftover invalid
        # references, which this test is supposed to find
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 2)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertEqual(doc1['creatorId'], user1['_id'])

        # Delete user and test post-delete
        self.model('user').remove(user1)
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertIsNone(doc1.get('creatorId'))

        # Delete group and test post-delete
        self.model('group').remove(group1)
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 0)
        self.assertIsNone(doc1.get('creatorId'))
