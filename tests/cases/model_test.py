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

import os

from .. import base
from girder.models.model_base import AccessControlledModel, AccessException, AccessType, Model
from girder.models.group import Group
from girder.models.user import User
from girder.utility.acl_mixin import AccessControlMixin


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


class FakeAcMixinModel(AccessControlMixin, Model):
    def initialize(self):
        self.name = 'fake_ac_mixin'
        self.resourceColl = 'fake_ac'
        self.resourceParent = 'fakeParentId'

    def validate(self, doc):
        return doc


class FakeAttachedModel(AccessControlMixin, Model):
    def initialize(self):
        self.name = 'fake_attached'

    def validate(self, doc):
        return doc


def setUpModule():
    base.mockPluginDir(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_plugins'))
    base.enabledPlugins.append('has_model')

    base.startServer()

    global FakeAcPluginModel
    from girder.plugins.has_model.models.fake_ac_plugin_model import FakeAcPluginModel


def tearDownModule():
    base.stopServer()


class ModelTestCase(base.TestCase):
    """
    Unit test the model-related functionality and utilities.
    """
    def setUp(self):
        base.TestCase.setUp(self)

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
        retval = Model._supplementFields(inclusionProjDict, overrideFields)
        assertItemsEqual(retval, inclusionProjDict)
        assertItemsEqual(inclusionProjDict, copy)
        retval = Model._supplementFields(inclusionProjList, overrideFields)
        assertItemsEqual(retval, inclusionProjList)
        retval = Model._supplementFields(exclusionProjDict, {'newValue'})
        assertItemsEqual(retval, exclusionProjDict)
        retval = Model._supplementFields(inclusionProjDict, {'newValue'})
        assertItemsEqual(retval, {
            'public': True,
            'access': True,
            'email': True,
            'login': True,
            'newValue': True
        })
        retval = Model._supplementFields(exclusionProjDict, overrideFields)
        assertItemsEqual(retval, {'email': False, 'login': False})

        originalDoc = {
            '_id': '1234',
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'
        }
        doc = dict(originalDoc)
        Model._removeSupplementalFields(doc, exclusionProjDict)
        assertItemsEqual(doc, {
            '_id': '1234',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'})

        doc = dict(originalDoc)
        Model._removeSupplementalFields(doc, inclusionProjList)
        assertItemsEqual(doc, {
            '_id': '1234',
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'})

        doc = dict(originalDoc)
        Model._removeSupplementalFields(doc, inclusionProjDict)
        assertItemsEqual(doc, {
            '_id': '1234',
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'})

        # Test None edge cases
        retval = Model._supplementFields(None, {'access', 'public'})
        self.assertIsNone(retval)
        doc = dict(originalDoc)
        Model._removeSupplementalFields(doc, None)
        assertItemsEqual(doc, originalDoc)

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
        retval = Model._supplementFields(fields, overwrite)
        assertItemsEqual(retval, overwrittenFields)
        doc = {
            '_id': 'id',
            'login': 'login',
            'email': 'email@email.com',
            'firstName': 'fname',
            'lastName': 'lname'
        }
        Model._removeSupplementalFields(doc, fields)
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
        adminUser, regUser = [User().createUser(**user) for user in users]

        fields = {
            'hidden': 1,
            'read': 1,
            'write': 1,
            'write2': 1,
            'admin': 1,
            'sa': 1
        }
        # Test filter behavior on access controlled model
        fakeAc = FakeAcModel().save(fields)
        fakeAc = FakeAcModel().setUserAccess(fakeAc, regUser, level=AccessType.READ)

        filtered = FakeAcModel().filter(fakeAc, adminUser)
        self.assertTrue('sa' in filtered)
        self.assertTrue('write' in filtered)
        self.assertFalse('hidden' in filtered)

        FakeAcModel().exposeFields(level=AccessType.READ, fields='hidden')

        filtered = FakeAcModel().filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('read' in filtered)
        self.assertFalse('write' in filtered)
        self.assertFalse('admin' in filtered)
        self.assertFalse('sa' in filtered)

        FakeAcModel().hideFields(level=AccessType.READ, fields='read')

        fakeAc = FakeAcModel().setUserAccess(fakeAc, regUser, level=AccessType.ADMIN)

        filtered = FakeAcModel().filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('write' in filtered)
        self.assertTrue('admin' in filtered)
        self.assertFalse('read' in filtered)
        self.assertFalse('sa' in filtered)

        # Test Model implementation
        fake = FakeModel().save(fields)
        filtered = FakeModel().filter(fake, regUser)
        self.assertEqual(filtered, {'read': 1, '_modelType': 'fake'})

        filtered = FakeModel().filter(fake, adminUser)
        self.assertEqual(filtered, {
            'read': 1,
            'sa': 1,
            '_modelType': 'fake'
        })

    def testAccessControlCleanup(self):
        # Create documents
        user1 = User().createUser(
            email='guy@place.com',
            login='someguy',
            firstName='Some',
            lastName='Guy',
            password='mypassword'
        )
        user2 = User().createUser(
            email='other@place.com',
            login='otherguy',
            firstName='Other',
            lastName='Guy',
            password='mypassword2'
        )
        group1 = Group().createGroup(
            name='agroup',
            creator=user2
        )
        doc1 = {
            'creatorId': user1['_id'],
            'field1': 'value1',
            'field2': 'value2'
        }
        doc1 = FakeAcModel().setUserAccess(doc1, user1, level=AccessType.ADMIN)
        doc1 = FakeAcModel().setUserAccess(doc1, user2, level=AccessType.READ)
        doc1 = FakeAcModel().setGroupAccess(doc1, group1, level=AccessType.WRITE)
        doc1 = FakeAcModel().save(doc1)
        doc1Id = doc1['_id']

        # Test pre-delete
        # The raw ACL properties must be examined directly, as the
        # "getFullAccessList" method will silently remove leftover invalid
        # references, which this test is supposed to find
        doc1 = FakeAcModel().load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 2)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertEqual(doc1['creatorId'], user1['_id'])

        # Delete user and test post-delete
        User().remove(user1)
        doc1 = FakeAcModel().load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertIsNone(doc1.get('creatorId'))

        # Delete group and test post-delete
        Group().remove(group1)
        doc1 = FakeAcModel().load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 0)
        self.assertIsNone(doc1.get('creatorId'))

    def _assertWriteAccess(self, instanceId, user, modelType):
        self.assertRaises(AccessException, modelType().load, instanceId)
        self.assertRaises(
            AccessException, modelType().load,
            instanceId, level=AccessType.READ)
        self.assertIsNotNone(modelType().load(instanceId, force=True))
        self.assertIsNotNone(modelType().load(
            instanceId, user=user, level=AccessType.READ))
        self.assertRaises(
            AccessException, modelType().load,
            instanceId, user=user, level=AccessType.ADMIN)

    def testAccessControlMixin(self):
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
        adminUser, regUser = [User().createUser(**user) for user in users]

        # Set up a parent model, and check access
        parentInstance = FakeAcModel().save({})
        self.assertHasKeys(parentInstance, ['_id'])
        parentInstance = FakeAcModel().setUserAccess(
            parentInstance, regUser, level=AccessType.WRITE, save=True)
        self._assertWriteAccess(parentInstance['_id'], regUser, FakeAcModel)

        # Set up an access control mixin model, and check access
        dependentInstance = FakeAcMixinModel().save({
            'fakeParentId': parentInstance['_id']})
        self.assertHasKeys(dependentInstance, ['_id', 'fakeParentId'])
        self._assertWriteAccess(dependentInstance['_id'], regUser, FakeAcMixinModel)

        # Set up an attached model, and check access
        attachedInstance1 = FakeAttachedModel().save({
            'attachedToId': parentInstance['_id'],
            'attachedToType': 'fake_ac'})
        self.assertHasKeys(attachedInstance1, ['_id', 'attachedToId', 'attachedToType'])
        self._assertWriteAccess(attachedInstance1['_id'], regUser, FakeAttachedModel)

        # Set up a parent model from a plugin, and check access
        parentPluginInstance = FakeAcPluginModel().save({})
        self.assertHasKeys(parentPluginInstance, ['_id'])
        parentPluginInstance = FakeAcPluginModel().setUserAccess(
            parentPluginInstance, regUser, level=AccessType.WRITE, save=True)
        self._assertWriteAccess(parentPluginInstance['_id'], regUser, FakeAcPluginModel)

        # Set up an attached model, resourcing a plugin model, and check access
        attachedInstance2 = FakeAttachedModel().save({
            'attachedToId': parentPluginInstance['_id'],
            'attachedToType': ['fake_ac_plugin_model', 'has_model']})
        self.assertHasKeys(attachedInstance2, ['_id', 'attachedToId', 'attachedToType'])
        self._assertWriteAccess(attachedInstance2['_id'], regUser, FakeAttachedModel)
