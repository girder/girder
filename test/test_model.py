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

import pytest

from girder.models.model_base import AccessControlledModel, Model, AccessType
from girder.models.group import Group
from girder.models.user import User
from girder.utility import acl_mixin, model_importer


@pytest.fixture
def inclusionProjDict():
    yield {
        'public': True,
        'access': True,
        'email': True,
        'login': True
    }


@pytest.fixture
def overrideFields():
    yield {'access', 'public'}


@pytest.fixture
def inclusionProjList():
    yield ['public', 'access', 'email', 'login']


@pytest.fixture
def exclusionProjDict():
    yield {
        'public': False,
        'access': False,
        'email': False,
        'login': False
    }


class TestProjectionUtilsSupplementFields(object):

    def testInclusionProjectDictOverride(self, inclusionProjDict, overrideFields):
        copy = dict(inclusionProjDict)
        retval = Model._supplementFields(inclusionProjDict, overrideFields)
        assert retval == inclusionProjDict
        assert inclusionProjDict == copy

    def testInclusionProjListOverride(self, inclusionProjList, overrideFields):
        retval = Model._supplementFields(inclusionProjList, overrideFields)
        assert set(retval) == set(inclusionProjList)

    def testExclusionProjDictNewValue(self, exclusionProjDict):
        retval = Model._supplementFields(exclusionProjDict, {'newValue'})
        assert retval == exclusionProjDict

    def testInclusionProjDictNewValue(self, inclusionProjDict):
        retval = Model._supplementFields(inclusionProjDict, {'newValue'})
        assert retval == {
            'public': True,
            'access': True,
            'email': True,
            'login': True,
            'newValue': True
        }

    def testExclusionProjDictOverride(self, exclusionProjDict, overrideFields):
        retval = Model._supplementFields(exclusionProjDict, overrideFields)
        assert retval == {'email': False, 'login': False}

    def testNoneEdgeCase(self):
        # Test None edge cases
        retval = Model._supplementFields(None, {'access', 'public'})
        assert retval is None

    def testFalseInclusionEdgeCase(self):
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


class TestProjectionUtilsRemoveSupplementalFields(object):
    def testExclusionProjDict(self, doc, exclusionProjDict):
        Model._removeSupplementalFields(doc, exclusionProjDict)
        assert doc == {
            '_id': '1234',
            'password': 'password1',
            'admin': False,
            'firstName': 'first',
            'lastName': 'last'}

    def testInclusionProjList(self, doc, inclusionProjList):
        Model._removeSupplementalFields(doc, inclusionProjList)
        assert doc == {
            '_id': '1234',
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'}

    def testInclusionProjDict(self, doc, inclusionProjDict):
        Model._removeSupplementalFields(doc, inclusionProjDict)
        assert doc == {
            '_id': '1234',
            'public': True,
            'access': True,
            'email': 'email@email.com',
            'login': 'login'}

    def testNoneEdgeCase(self, doc):
        originalDoc = dict(doc)
        Model._removeSupplementalFields(doc, None)
        assert doc == originalDoc

    def testFlaseInclusionEdgeCase(self):
        doc = {
            '_id': 'id',
            'login': 'login',
            'email': 'email@email.com',
            'firstName': 'fname',
            'lastName': 'lname'
        }
        fields = {
            '_id': False,
            'login': True,
            'email': True,
            'firstName': True,
            'lastName': True
        }
        Model._removeSupplementalFields(doc, fields)
        assert doc == {
            'login': 'login',
            'email': 'email@email.com',
            'firstName': 'fname',
            'lastName': 'lname'}


class TestProjectionIsInclusionProjection(object):

    def testNone(self):
        assert Model._isInclusionProjection(None) is False

    def testEmptyDict(self):
        assert Model._isInclusionProjection({}) is True

    def testIdFalse(self):
        assert Model._isInclusionProjection({'_id': False}) is False

    def testIdTrue(self):
        assert Model._isInclusionProjection({'_id': True}) is True


@pytest.fixture
def doc():
    yield {
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


@pytest.fixture
def fields():
    yield {
        'hidden': 1,
        'read': 1,
        'write': 1,
        'write2': 1,
        'admin': 1,
        'sa': 1
    }


@pytest.fixture
def FakeAcModel():
    class FakeAcModelClass(AccessControlledModel):
        def initialize(self):
            self.name = 'fake_ac'

            self.exposeFields(level=AccessType.READ, fields='read')
            self.exposeFields(level=AccessType.WRITE, fields=('write', 'write2'))
            self.exposeFields(level=AccessType.ADMIN, fields='admin')
            self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

            self.ensureTextIndex({'name': 1})

        def validate(self, doc):
            return doc

    return FakeAcModelClass


class FakeModel(Model):
    def initialize(self):
        self.name = 'fake'

        self.exposeFields(level=AccessType.READ, fields='read')
        self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

        self.ensureTextIndex({'name': 1})

    def validate(self, doc):
        return doc


@pytest.fixture
def FakeAcMixModel(FakeAcModel):
    model_importer._modelClasses.setdefault('_core', {})['fake_ac'] = FakeAcModel

    class FakeAcMixModelClass(acl_mixin.AccessControlMixin, Model):
        def initialize(self):
            self.name = 'fake_acmix'

            self.resourceColl = 'fake_ac'
            self.resourceParent = 'parentId'

            self.ensureTextIndex({'name': 1})

        def validate(self, doc):
            return doc
    return FakeAcMixModelClass


class TestModelFiltering(object):
    def testFilterOnACLModel(self, admin, user, fields, FakeAcModel):
        # Test filter behavior on access controlled model
        fakeAc = FakeAcModel().save(fields)
        fakeAc = FakeAcModel().setUserAccess(fakeAc, user, level=AccessType.READ)

        filtered = FakeAcModel().filter(fakeAc, admin)
        assert 'sa' in filtered
        assert 'write' in filtered
        assert 'hidden' not in filtered

    def testExposeFields(self, admin, user, fields, FakeAcModel):
        fakeAc = FakeAcModel().save(fields)
        fakeAc = FakeAcModel().setUserAccess(fakeAc, user, level=AccessType.READ)
        FakeAcModel().exposeFields(level=AccessType.READ, fields='hidden')

        filtered = FakeAcModel().filter(fakeAc, user)
        assert 'hidden' in filtered
        assert 'read' in filtered
        assert 'write' not in filtered
        assert 'admin' not in filtered
        assert 'sa' not in filtered

    def testHideFields(self, admin, user, fields, FakeAcModel):
        fakeAc = FakeAcModel().save(fields)
        FakeAcModel().hideFields(level=AccessType.READ, fields='read')
        fakeAc = FakeAcModel().setUserAccess(fakeAc, user, level=AccessType.ADMIN)
        filtered = FakeAcModel().filter(fakeAc, user)
        assert 'hidden' not in filtered
        assert 'write' in filtered
        assert 'admin' in filtered
        assert 'read' not in filtered
        assert 'sa' not in filtered

    def testFilterNonACLModel(self, admin, user, fields):
        fake = FakeModel().save(fields)
        filtered = FakeModel().filter(fake, user)
        assert filtered == {'read': 1, '_modelType': 'fake'}

        filtered = FakeModel().filter(fake, admin)
        assert filtered == {
            'read': 1,
            'sa': 1,
            '_modelType': 'fake'
        }


@pytest.fixture
def group(user):
    g = Group().createGroup(
        name='agroup',
        creator=user
    )
    yield g


@pytest.fixture
def documentWithGroup(group, admin, user, FakeAcModel):
    # Create documents
    user1 = admin
    user2 = user
    group1 = group
    doc1 = {
        'creatorId': user1['_id'],
        'field1': 'value1',
        'field2': 'value2'
    }
    doc1 = FakeAcModel().setUserAccess(doc1, user1, level=AccessType.ADMIN)
    doc1 = FakeAcModel().setUserAccess(doc1, user2, level=AccessType.READ)
    doc1 = FakeAcModel().setGroupAccess(doc1, group1, level=AccessType.WRITE)
    doc1 = FakeAcModel().save(doc1)
    yield doc1


class TestAccessControlCleanup(object):
    def testAccessControlPreDelete(self, admin, documentWithGroup, FakeAcModel):
        docId = documentWithGroup['_id']
        doc1 = FakeAcModel().load(docId, force=True, exc=True)
        assert len(doc1['access']['users']) == 2
        assert len(doc1['access']['groups']) == 1
        assert doc1['creatorId'] == admin['_id']

    def testUserPostDeleteCleanup(self, admin, documentWithGroup, FakeAcModel):
        docId = documentWithGroup['_id']
        User().remove(admin)
        doc1 = FakeAcModel().load(docId, force=True, exc=True)
        assert len(doc1['access']['users']) == 1
        assert len(doc1['access']['groups']) == 1
        assert doc1.get('creatorId') is None

    def testGroupPostDeleteCleanup(self, group, documentWithGroup, FakeAcModel):
        # Delete group and test post-delete
        docId = documentWithGroup['_id']
        Group().remove(group)
        doc1 = FakeAcModel().load(docId, force=True, exc=True)
        assert len(doc1['access']['users']) == 2
        assert len(doc1['access']['groups']) == 0
        assert doc1.get('creatorId') is not None


def testTextSearch(db):
    FakeModel().save({'name': 'first name'})
    FakeModel().save({'name': 'second name'})
    FakeModel().save({'name': 'second second'})
    FakeModel().save({'name': 'fourth names'})
    assert FakeModel().textSearch('names').count() == 3
    assert FakeModel().textSearch('"names"').count() == 1
    assert FakeModel().textSearch('second').count() == 2
    assert FakeModel().textSearch('unknown').count() == 0


def makeDocumentWithPermissions(
        model, name, admin=None, adminLevel=None, user=None, userLevel=None,
        group=None, groupLevel=None):
    doc = {
        'creatorId': (admin or user)['_id'],
        'name': name,
        'field1': 'value1',
        'field2': 'value2'
    }
    if admin is not None and adminLevel is not None:
        doc = model.setUserAccess(doc, admin, level=adminLevel)
    if user is not None and userLevel is not None:
        doc = model.setUserAccess(doc, user, level=userLevel)
    if group is not None and groupLevel is not None:
        doc = model.setGroupAccess(doc, group, level=groupLevel)
    doc = model.save(doc)
    return doc


class TestFindWithPermissions(object):
    def generalTest(self, _model, admin, user):
        query, fields = _model._textSearchFilters('names')
        # Test with permissions
        assert _model.findWithPermissions(
            query, fields=fields, user=admin).count() == 3
        assert _model.findWithPermissions(
            query, fields=fields, user=user).count() == 2
        assert _model.findWithPermissions(
            query, fields=fields, user=None).count() == 0
        assert _model.findWithPermissions(
            query, fields=fields, user=user, level=AccessType.WRITE).count() == 1
        assert _model.findWithPermissions(
            query, fields=fields, user=None, level=AccessType.WRITE).count() == 0
        # Test with offset
        assert len(list(_model.findWithPermissions(
            query, fields=fields, user=admin))) == 3
        assert len(list(_model.findWithPermissions(
            query, fields=fields, user=admin, offset=1))) == 2
        assert len(list(_model.findWithPermissions(
            query, fields=fields, user=user))) == 2
        assert len(list(_model.findWithPermissions(
            query, fields=fields, user=user, offset=1))) == 1

        # Ensure timeout is accepted
        assert _model.findWithPermissions(
            query, fields=fields, user=user, timeout=5).count() == 2
        assert _model.findWithPermissions(
            query, fields=fields, user=user, timeout=0).count() == 2

        # Test with fields
        for currentUser in (user, admin):
            query, fields = _model._textSearchFilters('names')
            assert 'name' in _model.findWithPermissions(
                query, fields=fields, user=currentUser).next()
            assert 'field1' in _model.findWithPermissions(
                query, fields=fields, user=currentUser).next()
            query, fields = _model._textSearchFilters('names', fields={'name': True})
            assert 'name' in _model.findWithPermissions(
                query, fields=fields, user=currentUser).next()
            assert 'field1' not in _model.findWithPermissions(
                query, fields=fields, user=currentUser).next()

    def testFindWithPermissions(self, db, admin, user, group, FakeAcModel):
        _model = FakeAcModel()
        makeDocumentWithPermissions(
            _model, 'first name', admin, AccessType.ADMIN,
            user, AccessType.READ, group, AccessType.WRITE)
        makeDocumentWithPermissions(
            _model, 'second name', admin, AccessType.ADMIN)
        makeDocumentWithPermissions(
            _model, 'second second', admin, AccessType.ADMIN,
            user, AccessType.READ)
        makeDocumentWithPermissions(
            _model, 'fourth names', admin, AccessType.ADMIN,
            user, AccessType.WRITE, group, AccessType.WRITE)
        self.generalTest(_model, admin, user)

    def testFindWithPermissionsAcMix(self, db, admin, user, group, FakeAcModel, FakeAcMixModel):
        _model = FakeAcMixModel()
        d1 = makeDocumentWithPermissions(
            FakeAcModel(), 'd1', admin, AccessType.ADMIN,
            user, AccessType.READ, group, AccessType.WRITE)
        d2 = makeDocumentWithPermissions(
            FakeAcModel(), 'd2', admin, AccessType.ADMIN)
        d3 = makeDocumentWithPermissions(
            FakeAcModel(), 'd3', admin, AccessType.ADMIN,
            user, AccessType.READ)
        d4 = makeDocumentWithPermissions(
            FakeAcModel(), 'd4', admin, AccessType.ADMIN,
            user, AccessType.WRITE, group, AccessType.WRITE)
        _model.save({'name': 'first name', 'parentId': d1['_id'], 'field1': 'value1'})
        _model.save({'name': 'second name', 'parentId': d2['_id'], 'field1': 'value1'})
        _model.save({'name': 'second second', 'parentId': d3['_id'], 'field1': 'value1'})
        _model.save({'name': 'fourth names', 'parentId': d4['_id'], 'field1': 'value1'})
        self.generalTest(_model, admin, user)
