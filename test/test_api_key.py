# -*- coding: utf-8 -*-
import datetime
import json
import pytest

from girder.constants import TokenScope
from girder.exceptions import ValidationException
from girder.models.api_key import ApiKey
from girder.models.setting import Setting
from girder.models.token import Token
from girder.settings import SettingKey
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def apiKey(server, user):
    # Create a new API key with full access
    resp = server.request('/api_key', method='POST', params={
        'name': 'test key'
    }, user=user)
    assertStatusOk(resp)
    apiKey = ApiKey().load(resp.json['_id'], force=True)

    yield apiKey


def testListScopes(server):
    resp = server.request('/token/scopes')
    assertStatusOk(resp)
    assert resp.json == TokenScope.listScopes()

    assert 'custom' in resp.json
    assert isinstance(resp.json['custom'], list)
    assert 'adminCustom' in resp.json
    assert isinstance(resp.json['adminCustom'], list)

    for scope in resp.json['custom'] + resp.json['adminCustom']:
        assert 'id' in scope
        assert 'name' in scope
        assert 'description' in scope


def testUserCannotAccessOtherApiKeys(server, admin, user):
    # Normal users shouldn't be able to request other users' keys
    resp = server.request('/api_key', params={'userId': admin['_id']},
                          user=user)
    assertStatus(resp, 403)
    assert resp.json['message'] == 'Administrator access required.'


def testUserCanAccessTheirOwnApiKeys(server, user):
    # Users should be able to request their own keys
    resp = server.request('/api_key', params={'userId': user['_id']},
                          user=user)
    assertStatusOk(resp)
    assert resp.json == []


def testUserCanAccessApiKeysWithoutUserId(server, user):
    # Passing no user ID should work
    resp = server.request('/api_key', user=user)
    assertStatusOk(resp)
    assert resp.json == []


def testAdminCanAccessOtherUsersKeys(server, admin, user):
    # Admins should be able to see other users' keys
    resp = server.request('/api_key', params={'userId': user['_id']},
                          user=admin)
    assertStatusOk(resp)
    assert resp.json == []


def testApiKeyCreation(server, user, apiKey):
    assert apiKey['scope'] is None
    assert apiKey['name'] == 'test key'
    assert apiKey['lastUse'] is None
    assert apiKey['tokenDuration'] is None
    assert apiKey['active'] is True


def testTokenCreation(server, user, apiKey):
    defaultDuration = Setting().get(SettingKey.COOKIE_LIFETIME)
    # Create a token using the key
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key'],
        'duration': defaultDuration + 1000
    })
    assertStatusOk(resp)
    token = Token().load(
        resp.json['authToken']['token'], force=True, objectId=False)
    # Make sure token has full user auth access
    assert token['userId'] == user['_id']
    assert token['scope'] == [TokenScope.USER_AUTH]
    # Make sure the token references the API key used to create it
    assert token['apiKeyId'] == apiKey['_id']

    # Make sure the token duration is not longer than the default
    duration = token['expires'] - token['created']
    assert duration == datetime.timedelta(days=defaultDuration)


def testTokenCreationDuration(server, user, apiKey):
    defaultDuration = Setting().get(SettingKey.COOKIE_LIFETIME)
    # We should be able to request a duration shorter than default
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key'],
        'duration': defaultDuration - 1
    })
    assertStatusOk(resp)
    token = Token().load(
        resp.json['authToken']['token'], force=True, objectId=False)
    duration = token['expires'] - token['created']
    assert duration == datetime.timedelta(days=defaultDuration - 1)


def testTokenCreatesUniqueTokens(server, user, apiKey):
    for _ in range(0, 2):
        resp = server.request('/api_key/token', method='POST', params={
            'key': apiKey['key']
        })
        assertStatusOk(resp)

    # We should have two tokens for this key
    q = {
        'userId': user['_id'],
        'apiKeyId': apiKey['_id']
    }
    count = Token().find(q).count()
    assert count == 2


def testInactiveKeyStructure(server, user, apiKey):
    newScopes = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
    resp = server.request('/api_key/%s' % apiKey['_id'], params={
        'active': False,
        'tokenDuration': 10,
        'scope': json.dumps(newScopes)
    }, method='PUT', user=user)
    assertStatusOk(resp)

    # Make sure key itself didn't change
    assert resp.json['key'] == apiKey['key']
    apiKey = ApiKey().load(resp.json['_id'], force=True)
    assert not apiKey['active']
    assert apiKey['tokenDuration'] == 10
    assert set(apiKey['scope']) == set(newScopes)


def testInactiveKeysCannotCreateTokens(server, user, apiKey):
    newScopes = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
    resp = server.request('/api_key/%s' % apiKey['_id'], params={
        'active': False,
        'tokenDuration': 10,
        'scope': json.dumps(newScopes)
    }, method='PUT', user=user)
    assertStatusOk(resp)

    # We should not be able to create tokens for this key anymore
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key']
    })
    assertStatus(resp, 400)
    assert resp.json['message'] == 'Invalid API key.'


def testDeactivatingKeyDeletesAssociatedTokens(server, user, apiKey):
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key']
    })
    assertStatusOk(resp)

    newScopes = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
    resp = server.request('/api_key/%s' % apiKey['_id'], params={
        'active': False,
        'tokenDuration': 10,
        'scope': json.dumps(newScopes)
    }, method='PUT', user=user)
    assertStatusOk(resp)

    # This should have deleted all corresponding tokens
    q = {
        'userId': user['_id'],
        'apiKeyId': apiKey['_id']
    }
    count = Token().find(q).count()
    assert count == 0


def testReactivatedKeyCanCreateTokens(server, user, apiKey):
    newScopes = [TokenScope.DATA_READ, TokenScope.DATA_WRITE]
    resp = server.request('/api_key/%s' % apiKey['_id'], params={
        'active': False,
        'tokenDuration': 10,
        'scope': json.dumps(newScopes)
    }, method='PUT', user=user)
    assertStatusOk(resp)

    resp = server.request('/api_key/%s' % apiKey['_id'], params={
        'active': True
    }, method='PUT', user=user)
    assertStatusOk(resp)
    assert resp.json['key'] == apiKey['key']
    apiKey = ApiKey().load(resp.json['_id'], force=True)

    # Should now be able to make tokens with 10 day duration
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key']
    })
    assertStatusOk(resp)
    token = Token().load(
        resp.json['authToken']['token'], force=True, objectId=False)
    duration = token['expires'] - token['created']
    assert duration == datetime.timedelta(days=10)
    assert set(token['scope']) == set(newScopes)


def testApiKeyDeletionDeletesAssociatedTokens(server, user, apiKey):
    resp = server.request('/api_key/token', method='POST', params={
        'key': apiKey['key']
    })
    assertStatusOk(resp)

    q = {
        'userId': user['_id'],
        'apiKeyId': apiKey['_id']
    }

    # Deleting the API key should delete the tokens made with it
    count = Token().find(q).count()
    assert count == 1
    resp = server.request('/api_key/%s' % apiKey['_id'], method='DELETE', user=user)
    assertStatusOk(resp)
    count = Token().find(q).count()
    assert count == 0


def testScopeValidation(db, admin, user):
    # Make sure normal user cannot request admin scopes
    requestedScopes = [TokenScope.DATA_OWN, TokenScope.SETTINGS_READ]

    with pytest.raises(ValidationException, match='Invalid scopes: %s.$' %
                       TokenScope.SETTINGS_READ):
        ApiKey().createApiKey(user=user, name='', scope=requestedScopes)

    # Make sure an unregistered scope cannot be set on an API key
    requestedScopes = [TokenScope.DATA_OWN, TokenScope.SETTINGS_READ, 'nonsense']

    with pytest.raises(ValidationException, match='Invalid scopes: nonsense.$'):
        ApiKey().createApiKey(user=admin, name='', scope=requestedScopes)


def testDisableApiKeysSetting(server, user):
    errMsg = 'API key functionality is disabled on this instance.'

    resp = server.request('/api_key', method='POST', user=user, params={
        'name': 'test key'
    })
    assertStatusOk(resp)

    # Disable API keys
    Setting().set(SettingKey.API_KEYS, False)

    # Key should still exist
    key = ApiKey().load(resp.json['_id'], force=True, exc=True)

    # No longer possible to authenticate with existing key
    resp = server.request('/api_key/token', method='POST', params={
        'key': key['key']
    })
    assertStatus(resp, 400)
    assert resp.json['message'] == errMsg

    # No longer possible to create new keys
    resp = server.request('/api_key', method='POST', user=user, params={
        'name': 'should not work'
    })
    assertStatus(resp, 400)
    assert resp.json['message'] == errMsg

    # Still possible to delete key
    resp = server.request('/api_key/%s' % key['_id'], method='DELETE', user=user)
    assertStatusOk(resp)
    assert ApiKey().load(key['_id'], force=True) is None
