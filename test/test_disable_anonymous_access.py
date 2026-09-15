"""
Tests for the core.disable_anonymous_access setting.
"""
import pytest

from girder.exceptions import ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.settings import SettingKey
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def public_collection(db):
    """Create a public collection."""
    yield Collection().createCollection('Public Collection', public=True)


@pytest.fixture
def private_collection(db):
    """Create a private collection."""
    yield Collection().createCollection('Private Collection', public=False)


@pytest.fixture
def public_folder(db, user):
    """Create a public folder owned by 'user'."""
    folder = Folder().createFolder(
        parent=user, parentType='user',
        creator=user, name='Public Folder', public=True
    )
    yield folder


class TestDisableAnonymousAccessSetting:
    """Tests for the core.disable_anonymous_access setting validation."""

    def testSettingValidationTrue(self, db):
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        assert Setting().get(SettingKey.DISABLE_ANONYMOUS_ACCESS) is True
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)
        assert Setting().get(SettingKey.DISABLE_ANONYMOUS_ACCESS) is False

    def testSettingValidationInvalid(self, db):
        for invalid in [1, 'true', None, [], {}]:
            with pytest.raises(ValidationException):
                Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, invalid)

    def testSettingDefaultIsFalse(self, db):
        # Ensure default is False
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)
        assert Setting().get(SettingKey.DISABLE_ANONYMOUS_ACCESS) is False


class TestDisableAnonymousAccessFunctional:
    """Functional tests for core.disable_anonymous_access on public resources."""

    def testAnonymousCanAccessPublicCollectionByDefault(self, server, public_collection):
        """Anonymous users should be able to access public collections when setting is disabled."""
        resp = server.request(path='/collection/%s' % public_collection['_id'])
        assertStatusOk(resp)
        assert resp.json['public'] is True

    def testAnonymousCannotAccessPublicCollectionWhenEnabled(self, server, public_collection):
        """Anonymous users should NOT be able to access public collections"""
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/collection/%s' % public_collection['_id'])
            # Should return 401 Unauthorized
            assertStatus(resp, 401)
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)

    def testLoggedInUserCanAccessPublicCollectionWhenEnabled(self, server, public_collection, user):
        """Logged-in users should still be able to access public collections"""
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/collection/%s' % public_collection['_id'], user=user)
            assertStatusOk(resp)
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)

    def testAnonymousCannotAccessPrivateCollection(self, server, private_collection):
        """Anonymous users should not be able to access private collections regardless"""
        # Default behavior
        resp = server.request(path='/collection/%s' % private_collection['_id'])
        assertStatus(resp, 401)

        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/collection/%s' % private_collection['_id'])
            assertStatus(resp, 401)
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)

    def testAdminCanAccessPublicCollectionWhenEnabled(self, server, public_collection, admin):
        """Site administrators should still be able to access public collections."""
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/collection/%s' % public_collection['_id'], user=admin)
            assertStatusOk(resp)
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)

    def testAnonymousCanAccessPublicFolderByDefault(self, server, public_folder):
        """Anonymous users should be able to access public folders when setting is disabled."""
        resp = server.request(path='/folder/%s' % public_folder['_id'])
        assertStatusOk(resp)
        assert resp.json['public'] is True

    def testAnonymousCannotAccessPublicFolderWhenEnabled(self, server, public_folder):
        """Anonymous users should NOT be able to access public folders when setting is enabled."""
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/folder/%s' % public_folder['_id'])
            assertStatus(resp, 401)
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)

    def testAnonymousListPublicCollectionsDefault(self, server, public_collection):
        """Anonymous users should see public collections in the list by default."""
        resp = server.request(path='/collection')
        assertStatusOk(resp)
        assert any(c['public'] for c in resp.json)

    def testAnonymousListPublicCollectionsWhenEnabled(self, server, public_collection):
        """Anonymous users should NOT see public collections in the list when enabled."""
        Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, True)
        try:
            resp = server.request(path='/collection')
            # Should return 200 with an empty list because public resources are hidden
            assertStatusOk(resp)
            assert resp.json == []
        finally:
            Setting().set(SettingKey.DISABLE_ANONYMOUS_ACCESS, False)
