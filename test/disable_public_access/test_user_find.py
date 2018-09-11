import pytest

from girder.models.user import User


@pytest.mark.plugin('disable_public_access')
def testNoUserFindWithPermissions(user, admin):
    resp = list(User().findWithPermissions({}, user=None))
    assert len(resp) == 0


@pytest.mark.plugin('disable_public_access')
def testUserFindWithPermissions(user, admin):
    resp = list(User().findWithPermissions({}, user=user))
    assert len(resp) == 1


@pytest.mark.plugin('disable_public_access')
def testAdminFindWithPermissions(user, admin):
    resp = list(User().findWithPermissions({}, user=admin))
    assert len(resp) == 2


@pytest.mark.plugin('disable_public_access')
def testNoUserSearch(user, admin):
    resp = list(User().search(user=None))
    assert len(resp) == 0


@pytest.mark.plugin('disable_public_access')
def testUserSearch(user, admin):
    resp = list(User().search(user=user))
    assert len(resp) == 1


@pytest.mark.plugin('disable_public_access')
def testAdminSearch(user, admin):
    resp = list(User().search(user=admin))
    assert len(resp) == 2
