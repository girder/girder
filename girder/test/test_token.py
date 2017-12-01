import pytest
import random

from girder.constants import TokenScope
from girder.exceptions import AccessException
from girder.models.token import genToken, Token
from pytest_girder.assertions import assertStatus, assertStatusOk


@pytest.fixture
def token(server):
    resp = server.request(path='/token/session', method='GET')
    assertStatusOk(resp)
    yield resp.json['token']


def testTokenGenerationIsUnaffectedByNormalRandom():
    # Make sure we are not using the normal random to generate tokens
    random.seed(1)
    token1 = genToken()
    random.seed(1)
    token2 = genToken()

    assert token1 != token2


def testHasScope(db):
    scope = TokenScope.DATA_READ
    tokenModel = Token()
    token = tokenModel.createToken(scope=scope)

    # If token is None should return False
    assert not tokenModel.hasScope(None, scope)

    # If scope is None should return True
    assert tokenModel.hasScope(token, None)


def testRequireScope(db):
    scope = TokenScope.DATA_OWN
    anotherScope = TokenScope.SETTINGS_READ
    tokenModel = Token()
    token = tokenModel.createToken(scope=scope)

    # If specified scope does not exist raise an error
    with pytest.raises(AccessException):
        tokenModel.requireScope(token, anotherScope)


def testTokenSessionReturnsUniqueTokens(server, token):
    # If we ask for another token, we should get a different one
    resp = server.request(path='/token/session', method='GET')
    assertStatusOk(resp)
    token2 = resp.json['token']
    assert token != token2


def testTokenSessionReturnsPassedToken(server, token):
    # If we ask for another token, passing in the first one, we should get
    # the first one back
    resp = server.request(path='/token/session', method='GET', token=token)
    assertStatusOk(resp)
    token2 = resp.json['token']
    assert token == token2


def testTokenCurrentReturnsNone(server):
    # If we ask about the current token without passing one, we should get
    # null
    resp = server.request(path='/token/current', method='GET')
    assertStatusOk(resp)
    assert resp.json is None


def testTokenCurrentReturnsPassedToken(server, token):
    # With a token, we get the token document in the response
    resp = server.request(path='/token/current', method='GET', token=token)
    assertStatusOk(resp)
    assert token == resp.json['_id']


def testTokenSessionDeletionFailsWithoutToken(server):
    # Trying to delete a token without specifying one results in an error
    resp = server.request(path='/token/session', method='DELETE')
    assertStatus(resp, 401)


def testTokenSessionDeletion(server, token):
    # With the token should succeed
    resp = server.request(path='/token/session', method='DELETE', token=token)
    assertStatusOk(resp)
    # Now the token is gone, so it should fail
    resp = server.request(path='/token/session', method='DELETE', token=token)
    assertStatus(resp, 401)
