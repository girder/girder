# -*- coding: utf-8 -*-
import pytest

from girder.api.rest import loadmodel, Resource
from girder.api import access
from girder.constants import AccessType, TokenScope
from girder.models.user import User
from girder.models.token import Token
from girder.settings import SettingKey
from pytest_girder.assertions import assertStatus, assertStatusOk


CUSTOM_SCOPE = 'Some.Exclusive.Scope'


# We deliberately don't have an access decorator
def defaultFunctionHandler(**kwargs):
    return


@access.admin
def adminFunctionHandler(**kwargs):
    return


@access.user
def userFunctionHandler(**kwargs):
    return


@access.public
def publicFunctionHandler(**kwargs):
    return


@access.token(scope=CUSTOM_SCOPE, required=True)
def requireScope(**kwargs):
    return


@access.public
@loadmodel(map={'id': 'user'}, model='user', level=AccessType.READ)
def plainFn(user, params):
    return user


@access.public
@loadmodel(map={'userId': 'user'}, model='user', level=AccessType.READ)
def loadModelWithMap(user, params):
    return user


class AccessTestResource(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'accesstest'
        self.route('GET', ('default_access', ), self.defaultHandler)
        self.route('GET', ('admin_access', ), self.adminHandler)
        self.route('GET', ('user_access', ), self.userHandler)
        self.route('GET', ('public_access', ), self.publicHandler)
        self.route('GET', ('cookie_auth', ), self.cookieHandler)
        self.route('POST', ('cookie_auth', ), self.cookieHandler)
        self.route('GET', ('scoped_cookie_auth', ), self.cookieScopedHandler)
        self.route('GET', ('fn_admin', ), self.fnAdmin)
        self.route('GET', ('scoped_user', ), self.scopedUser)
        self.route('GET', ('fn_public', ), self.fnPublic)
        self.route('GET', ('scoped_public', ), self.scopedPublic)

    # We deliberately don't have an access decorator
    def defaultHandler(self, **kwargs):
        return

    @access.admin
    def adminHandler(self, **kwargs):
        return

    @access.user
    def userHandler(self, **kwargs):
        return

    @access.public
    def publicHandler(self, **kwargs):
        return self.getCurrentUser()

    @access.user(cookie=True)
    def cookieHandler(self, **kwargs):
        return

    @access.user(scope=TokenScope.DATA_READ, cookie=True)
    def cookieScopedHandler(self, **kwargs):
        return

    @access.admin()
    def fnAdmin(self, **kwargs):
        return

    @access.user(scope=TokenScope.DATA_READ)
    def scopedUser(self, **kwargs):
        return

    @access.public()
    def fnPublic(self, **kwargs):
        return self.getCurrentUser()

    @access.public(scope=TokenScope.SETTINGS_READ)
    def scopedPublic(self, **kwargs):
        return self.getCurrentUser()


@pytest.fixture
def server(server):
    server.root.api.v1.accesstest = AccessTestResource()
    # Public access endpoints do not need to be a Resource subclass method,
    # they can be a regular function
    accesstest = server.root.api.v1.accesstest
    accesstest.route('GET', ('default_function_access', ),
                     defaultFunctionHandler)
    accesstest.route('GET', ('admin_function_access', ), adminFunctionHandler)
    accesstest.route('GET', ('user_function_access', ), userFunctionHandler)
    accesstest.route('GET', ('public_function_access', ),
                     publicFunctionHandler)
    accesstest.route('GET', ('test_loadmodel_plain', ':id'), plainFn)
    accesstest.route('GET', ('test_loadmodel_query',), loadModelWithMap)
    accesstest.route('GET', ('test_required_scope_exists', ), requireScope)

    yield server


@pytest.fixture
def cookie(user):
    yield 'girderToken=%s' % str(Token().createToken(user)['_id'])


@pytest.fixture
def adminSettingToken(db, admin):
    yield Token().createToken(user=admin, scope=TokenScope.SETTINGS_READ)


@pytest.fixture
def adminEmailToken(db, admin):
    yield Token().createToken(user=admin, scope=TokenScope.DATA_READ)


@pytest.fixture
def userDataReadToken(db, user):
    yield Token().createToken(user=user, scope=TokenScope.DATA_READ)


@pytest.fixture
def userSettingToken(db, user):
    yield Token().createToken(user=user, scope=TokenScope.SETTINGS_READ)


@pytest.fixture
def userToken(db, user):
    yield Token().createToken(user=user)


public_endpoints = ['/accesstest/public_function_access', '/accesstest/public_access',
                    '/accesstest/fn_public', '/accesstest/scoped_public']
user_endpoints = ['/accesstest/user_access', '/accesstest/scoped_user',
                  '/accesstest/user_function_access']
admin_endpoints = ['/accesstest/default_access',
                   '/accesstest/admin_access',
                   '/accesstest/fn_admin',
                   '/accesstest/default_function_access',
                   '/accesstest/admin_function_access']


@pytest.mark.parametrize('endpoint', public_endpoints)
def testPublicCanAccessPublicEndpoints(server, endpoint):
    resp = server.request(path=endpoint, method='GET')
    assertStatusOk(resp)
    assert resp.json is None


@pytest.mark.parametrize('endpoint', user_endpoints + admin_endpoints)
def testPublicCannotAccessNonPublicEndpoints(server, endpoint):
    resp = server.request(path=endpoint, method='GET')
    assertStatus(resp, 401)


@pytest.mark.parametrize('endpoint', public_endpoints + user_endpoints)
def testUserCanAccessUserEndpoints(server, user, endpoint):
    resp = server.request(path=endpoint, method='GET', user=user)
    assertStatusOk(resp)


@pytest.mark.parametrize('endpoint', admin_endpoints)
def testUserCannotAccessAdminEndpoints(server, user, endpoint):
    resp = server.request(path=endpoint, method='GET', user=user)
    assertStatus(resp, 403)


@pytest.mark.parametrize('endpoint', public_endpoints + user_endpoints + admin_endpoints)
def testAdminCanAccessAllEndpoints(server, admin, endpoint):
    resp = server.request(path=endpoint, method='GET', user=admin)
    assertStatusOk(resp)


@pytest.mark.parametrize('method', ['GET', 'POST'])
def testCookieAuthFailsWithNoAuth(server, method):
    resp = server.request(path='/accesstest/cookie_auth', method=method)
    assertStatus(resp, 401)


@pytest.mark.parametrize('method', ['GET', 'POST'])
def testTokenAuthSucceedsOnCookieAuthEndpoints(server, user, method):
    resp = server.request(path='/accesstest/cookie_auth', method=method, user=user)
    assertStatusOk(resp)


@pytest.mark.parametrize('method', ['GET', 'POST'])
def testCookieAuthWorks(server, user, cookie, method):
    resp = server.request(path='/accesstest/cookie_auth', method=method, cookie=cookie)
    assertStatusOk(resp)


def testCookieScopedPrefersToken(server, user):
    resp = server.request(
        path='/accesstest/cookie_auth', user=user,
        cookie='girderToken=thisisnotavalidtoken')
    assertStatusOk(resp)


def testLoadModelDecorator(server, user):
    resp = server.request(
        path='/accesstest/test_loadmodel_plain/%s' % user['_id'], method='GET')
    assertStatusOk(resp)
    assert resp.json['_id'] == str(user['_id'])

    resp = server.request(path='/accesstest/test_loadmodel_query', params={'userId': None})
    assertStatus(resp, 400)
    assert resp.json['message'] == 'Invalid ObjectId: None'


def testGetFullAccessList(db, admin):
    acl = User().getFullAccessList(admin)
    assert len(acl['users']) == 1


def testReadingSettingsAsAdmin(server, admin):
    # Reading settings as admin should work
    resp = server.request(path='/system/setting', params={
        'key': SettingKey.SMTP_PORT}, user=admin)
    assertStatusOk(resp)
    assert resp.json == 25


def testReadingSettingsAsUserShouldFail(server, user):
    # Reading setting as non-admin should fail
    resp = server.request(path='/system/setting', params={
        'key': SettingKey.SMTP_PORT}, user=user)
    assertStatus(resp, 403)


def testReadingSettingsWithAdminScopedToken(server, adminSettingToken):
    # Reading settings with a properly scoped token should work
    resp = server.request(path='/system/setting', params={
        'key': SettingKey.SMTP_PORT}, token=adminSettingToken)
    assertStatusOk(resp)
    assert resp.json == 25


def testReadingSettingsWithAdminEmailToken(server, adminEmailToken):
    # Reading settings with an improperly scoped token should fail
    resp = server.request(path='/system/setting', params={
        'key': SettingKey.SMTP_PORT}, token=adminEmailToken)
    assertStatus(resp, 401)


def testReadingSettingsWithUserToken(server, userSettingToken):
    # Non-admin user with this token scope should still not work
    resp = server.request(path='/system/setting', params={
        'key': SettingKey.SMTP_PORT}, token=userSettingToken)
    assertStatus(resp, 403)
    assert resp.json['message'] == 'Administrator access required.'


def testReadingAssetstoreWithSettingScopedToken(server, adminSettingToken):
    # The setting-scope token should not grant access to other endpoints
    resp = server.request(path='/assetstore', token=adminSettingToken)
    assertStatus(resp, 401)


@pytest.mark.parametrize('endpoint', ['/accesstest/admin_access',
                                      '/accesstest/fn_admin'])
def testAdminRawDecoratorIsEquivalentToReturnedDecorator(server, adminSettingToken, endpoint):
    resp = server.request(path=endpoint, token=adminSettingToken)
    assertStatus(resp, 401)


def testUserAccessToken(server, userDataReadToken):
    resp = server.request(path='/accesstest/user_access', token=userDataReadToken)
    assertStatus(resp, 401)


def testUserAccessTokenOnScopedEndpoint(server, userDataReadToken):
    resp = server.request(path='/accesstest/scoped_user', token=userDataReadToken)
    assertStatusOk(resp)


def testArtificialScopedAccess(server, admin, user, userDataReadToken, userToken):
    # Test public access
    for route in ('public_access', 'fn_public', 'scoped_public'):
        path = '/accesstest/%s' % route

        for t in (userDataReadToken, None):
            resp = server.request(path=path, token=t)
            assertStatusOk(resp)
            assert resp.json is None

        resp = server.request(path=path, token=userToken)
        assertStatusOk(resp)
        assert resp.json['_id'] == str(user['_id'])

    # Make a correctly scoped token, should work.
    token = Token().createToken(
        user=user, scope=TokenScope.SETTINGS_READ)
    resp = server.request(path=path, token=token)
    assertStatusOk(resp)
    assert resp.json['_id'] == str(user['_id'])


def testRequiredScopeExists(server, user):
    token = Token().createToken(scope=CUSTOM_SCOPE)

    resp = server.request(path='/accesstest/test_required_scope_exists')
    # If not given a user or a valid auth token the status should be 401
    assertStatus(resp, 401)

    resp2 = server.request(path='/accesstest/test_required_scope_exists',
                           user=user)
    # If the token does not have the CUSTOM_SCOPE the status should be 403
    assertStatus(resp2, 403)

    # If user is not given but the token has the correct scope
    # the status should be 200
    resp3 = server.request(path='/accesstest/test_required_scope_exists',
                           token=token)

    assertStatus(resp3, 200)
