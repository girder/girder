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

from girder.models.model_base import AccessControlledModel, Model, AccessType
from girder.models.group import Group
from girder.models.user import User


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


def testProjectionUtils(db):
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
    assert retval == inclusionProjDict
    assert inclusionProjDict == copy
    retval = Model._supplementFields(inclusionProjList, overrideFields)
    assert set(retval) == set(inclusionProjList)
    retval = Model._supplementFields(exclusionProjDict, {'newValue'})
    assert retval == exclusionProjDict
    retval = Model._supplementFields(inclusionProjDict, {'newValue'})
    assert retval == {
        'public': True,
        'access': True,
        'email': True,
        'login': True,
        'newValue': True
    }
    retval = Model._supplementFields(exclusionProjDict, overrideFields)
    assert retval == {'email': False, 'login': False}

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
    assert doc == {
        '_id': '1234',
        'password': 'password1',
        'admin': False,
        'firstName': 'first',
        'lastName': 'last'}

    doc = dict(originalDoc)
    Model._removeSupplementalFields(doc, inclusionProjList)
    assert doc == {
        '_id': '1234',
        'public': True,
        'access': True,
        'email': 'email@email.com',
        'login': 'login'}

    doc = dict(originalDoc)
    Model._removeSupplementalFields(doc, inclusionProjDict)
    assert doc == {
        '_id': '1234',
        'public': True,
        'access': True,
        'email': 'email@email.com',
        'login': 'login'}

    # Test None edge cases
    retval = Model._supplementFields(None, {'access', 'public'})
    assert retval is None
    doc = dict(originalDoc)
    Model._removeSupplementalFields(doc, None)
    assert doc == originalDoc

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
    assert retval == overwrittenFields
    doc = {
        '_id': 'id',
        'login': 'login',
        'email': 'email@email.com',
        'firstName': 'fname',
        'lastName': 'lname'
    }
    Model._removeSupplementalFields(doc, fields)
    assert doc == {
        'login': 'login',
        'email': 'email@email.com',
        'firstName': 'fname',
        'lastName': 'lname'}

    # Test _isInclusionProjection edge cases
    assert Model._isInclusionProjection(None) is False
    assert Model._isInclusionProjection({}) is True
    assert Model._isInclusionProjection({'_id': False}) is False
    assert Model._isInclusionProjection({'_id': True}) is True


def testModelFiltering(db):
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
    assert 'sa' in filtered
    assert 'write' in filtered
    assert not ('hidden' in filtered)

    FakeAcModel().exposeFields(level=AccessType.READ, fields='hidden')

    filtered = FakeAcModel().filter(fakeAc, regUser)
    assert 'hidden' in filtered
    assert 'read' in filtered
    assert not ('write' in filtered)
    assert not ('admin' in filtered)
    assert not ('sa' in filtered)

    FakeAcModel().hideFields(level=AccessType.READ, fields='read')

    fakeAc = FakeAcModel().setUserAccess(fakeAc, regUser, level=AccessType.ADMIN)

    filtered = FakeAcModel().filter(fakeAc, regUser)
    assert 'hidden' in filtered
    assert 'write' in filtered
    assert 'admin' in filtered
    assert not ('read' in filtered)
    assert not ('sa' in filtered)

    # Test Model implementation
    fake = FakeModel().save(fields)
    filtered = FakeModel().filter(fake, regUser)
    assert filtered == {'read': 1, '_modelType': 'fake'}

    filtered = FakeModel().filter(fake, adminUser)
    assert filtered == {
        'read': 1,
        'sa': 1,
        '_modelType': 'fake'
    }


def testAccessControlCleanup(db):
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
    assert len(doc1['access']['users']) == 2
    assert len(doc1['access']['groups']) == 1
    assert doc1['creatorId'] == user1['_id']

    # Delete user and test post-delete
    User().remove(user1)
    doc1 = FakeAcModel().load(doc1Id, force=True, exc=True)
    assert len(doc1['access']['users']) == 1
    assert len(doc1['access']['groups']) == 1
    assert doc1.get('creatorId') is None

    # Delete group and test post-delete
    Group().remove(group1)
    doc1 = FakeAcModel().load(doc1Id, force=True, exc=True)
    assert len(doc1['access']['users']) == 1
    assert len(doc1['access']['groups']) == 0
    assert doc1.get('creatorId') is None
