import json

import pytest

from girder.constants import ACCESS_FLAGS, AccessType, registerAccessFlag
from girder.models.folder import Folder
from pytest_girder.assertions import assertStatusOk

PUBLIC_FLAG = 'test_public_flag'
NON_PUBLIC_FLAG = 'test_non_public_flag'
UNREGISTERED_FLAG = 'test_unregistered_flag'


@pytest.fixture
def testFlags():
    saved = dict(ACCESS_FLAGS)
    registerAccessFlag(PUBLIC_FLAG, 'Public test flag')
    registerAccessFlag(NON_PUBLIC_FLAG, 'Non-public test flag', public=False)
    yield
    ACCESS_FLAGS.clear()
    ACCESS_FLAGS.update(saved)


@pytest.fixture
def publicFolder(admin, user, testFlags):
    folder = Folder().createFolder(
        parent=admin, parentType='user', creator=admin, name='public', public=True)
    Folder().setUserAccess(folder, user, AccessType.ADMIN, save=True)
    yield folder


def _storePublicFlags(folder, flags):
    """Write publicFlags directly to the database, bypassing setPublicFlags."""
    Folder().update({'_id': folder['_id']}, {'$set': {'publicFlags': flags}})
    return Folder().load(folder['_id'], force=True)


def testRegisterAccessFlagDefaultsToPublic(testFlags):
    assert ACCESS_FLAGS[PUBLIC_FLAG]['public'] is True
    assert ACCESS_FLAGS[NON_PUBLIC_FLAG]['public'] is False


def testAccessFlagEndpointIncludesPublic(server, testFlags):
    resp = server.request(path='/system/access_flag')
    assertStatusOk(resp)
    assert resp.json[PUBLIC_FLAG]['public'] is True
    assert resp.json[NON_PUBLIC_FLAG]['public'] is False


@pytest.mark.parametrize('mode', ['admin', 'nonAdmin', 'force'])
def testSetPublicFlagsDropsNonPublicFlags(admin, user, publicFolder, mode):
    kwargs = {
        'admin': {'user': admin},
        'nonAdmin': {'user': user},
        'force': {'force': True},
    }[mode]
    folder = Folder().setPublicFlags(
        publicFolder, [PUBLIC_FLAG, NON_PUBLIC_FLAG], save=True, **kwargs)
    assert folder['publicFlags'] == [PUBLIC_FLAG]
    assert Folder().load(folder['_id'], force=True)['publicFlags'] == [PUBLIC_FLAG]


@pytest.mark.parametrize('userKey', ['admin', 'user'])
def testSetPublicFlagsDropsUnregisteredFlags(admin, user, publicFolder, userKey):
    requester = admin if userKey == 'admin' else user
    folder = Folder().setPublicFlags(
        publicFolder, [PUBLIC_FLAG, UNREGISTERED_FLAG], user=requester, save=True)
    assert folder['publicFlags'] == [PUBLIC_FLAG]


def testSetPublicFlagsAppendDropsNonPublicFlags(admin, publicFolder):
    folder = _storePublicFlags(publicFolder, [NON_PUBLIC_FLAG])
    folder = Folder().setPublicFlags(
        folder, [PUBLIC_FLAG], user=admin, append=True, save=True)
    assert folder['publicFlags'] == [PUBLIC_FLAG]


def testAccessEndpointDropsNonPublicFlags(server, user, publicFolder):
    access = {
        key: [dict(entry, id=str(entry['id'])) for entry in entries]
        for key, entries in publicFolder['access'].items()
    }
    resp = server.request(
        path='/folder/%s/access' % publicFolder['_id'], method='PUT', user=user, params={
            'access': json.dumps(access),
            'publicFlags': json.dumps([PUBLIC_FLAG, NON_PUBLIC_FLAG]),
            'public': True,
        })
    assertStatusOk(resp)
    assert Folder().load(publicFolder['_id'], force=True)['publicFlags'] == [PUBLIC_FLAG]


def testHasAccessFlagsIgnoresStoredNonPublicFlags(user, publicFolder):
    # Simulate data written before the flag was non-public, or directly to the database.
    folder = _storePublicFlags(publicFolder, [PUBLIC_FLAG, NON_PUBLIC_FLAG])

    for requester in (None, user):
        assert Folder().hasAccessFlags(folder, requester, PUBLIC_FLAG)
        assert not Folder().hasAccessFlags(folder, requester, NON_PUBLIC_FLAG)
        assert not Folder().hasAccessFlags(folder, requester, [PUBLIC_FLAG, NON_PUBLIC_FLAG])


def testNonPublicFlagCanBeGrantedThroughAcl(admin, user, publicFolder):
    folder = _storePublicFlags(publicFolder, [NON_PUBLIC_FLAG])
    assert not Folder().hasAccessFlags(folder, user, NON_PUBLIC_FLAG)

    Folder().setUserAccess(folder, user, AccessType.READ, flags=[NON_PUBLIC_FLAG], save=True)
    folder = Folder().load(folder['_id'], force=True)
    assert Folder().hasAccessFlags(folder, user, NON_PUBLIC_FLAG)
    assert not Folder().hasAccessFlags(folder, None, NON_PUBLIC_FLAG)


def testSiteAdminHasNonPublicFlags(admin, publicFolder):
    assert Folder().hasAccessFlags(publicFolder, admin, NON_PUBLIC_FLAG)
