# -*- coding: utf-8 -*-
import pytest

from girder.exceptions import AccessException
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey
from pytest_girder.assertions import assertStatus, assertStatusOk


def testInitializeOtp(user):
    # The logic for the server hostname as the issuer cannot be tested here, since there is no
    # current request, but that logic is explicitly tested in testOtpApiWorkflow
    Setting().set(SettingKey.BRAND_NAME, 'Branded Girder')

    otpUris = User().initializeOtp(user)

    # A URI for TOTP should be returned
    assert otpUris['totpUri'].startswith('otpauth://')
    assert user['login'] in otpUris['totpUri']
    assert 'issuer=Branded%20Girder' in otpUris['totpUri']

    # OTP should not be enabled yet, since it's not finalized
    assert user['otp']['enabled'] is False
    # TOTP parameters should be generated
    assert 'totp' in user['otp']


def testHasOtpEnabled(user):
    assert User().hasOtpEnabled(user) is False

    User().initializeOtp(user)

    # OTP is not yet enabled
    assert User().hasOtpEnabled(user) is False

    user['otp']['enabled'] = True

    assert User().hasOtpEnabled(user) is True


def _tokenFromTotpUri(totpUri, valid=True):
    # Create an external TOTP instance
    from passlib.totp import TOTP
    totp = TOTP.from_uri(totpUri)

    # Generate a valid token
    otpToken = totp.generate().token

    if not valid:
        # Increment the token by 1 to invalidate it
        otpToken = '%06d' % ((int(otpToken) + 1) % int(1e6))

    return otpToken


def testVerifyOtp(server, user):
    # Enable OTP
    otpUris = User().initializeOtp(user)
    user['otp']['enabled'] = True

    # Generate an invalid token
    otpToken = _tokenFromTotpUri(otpUris['totpUri'], False)

    with pytest.raises(AccessException):
        User().verifyOtp(user, otpToken)

    # Generate a valid token
    otpToken = _tokenFromTotpUri(otpUris['totpUri'])
    # Verify the token, which should succeed without raising an exception
    User().verifyOtp(user, otpToken)

    # Re-verify the same token, which should fail
    # The "server" fixture is necessary for this to work
    with pytest.raises(AccessException):
        User().verifyOtp(user, otpToken)


def testAuthenticateWithOtp(user):
    # Providing an unnecessary token should fail
    with pytest.raises(AccessException):
        User().authenticate('user', 'password', '123456')

    # Enable OTP and save user
    otpUris = User().initializeOtp(user)
    user['otp']['enabled'] = True
    User().save(user)

    # Providing no token should now fail
    with pytest.raises(AccessException):
        User().authenticate('user', 'password')

    # Generate a valid token
    otpToken = _tokenFromTotpUri(otpUris['totpUri'])

    # Authenticate successfully with the valid token
    User().authenticate('user', 'password', otpToken)


def testAuthenticateWithOtpConcatenated(user):
    # Non-OTP-user authentication should still succeed with "otpToken=True"
    User().authenticate('user', 'password', True)

    # Enable OTP and save user
    otpUris = User().initializeOtp(user)
    user['otp']['enabled'] = True
    User().save(user)

    # Authentication should now fail
    with pytest.raises(AccessException):
        User().authenticate('user', 'password', True)

    # Generate a valid token
    otpToken = _tokenFromTotpUri(otpUris['totpUri'])

    # Authenticate successfully with the valid token
    User().authenticate('user', 'password' + otpToken, True)


def testOtpApiWorkflow(server, user):
    # Try to finalize OTP before it's been initialized
    resp = server.request(
        path='/user/%s/otp' % user['_id'], method='PUT', user=user,
        additionalHeaders=[('Girder-OTP', '123456')])
    # This should fail cleanly
    assertStatus(resp, 400)
    assert 'not initialized' in resp.json['message']

    # Try to disable OTP before it's been enabled
    resp = server.request(path='/user/%s/otp' % user['_id'], method='DELETE', user=user)
    # This should fail cleanly
    assertStatus(resp, 400)
    assert 'not enabled' in resp.json['message']

    # Initialize OTP
    resp = server.request(path='/user/%s/otp' % user['_id'], method='POST', user=user)
    assertStatusOk(resp)
    # Save the URI
    totpUri = resp.json['totpUri']

    # Test the logic for server hostname as OTP URI issuer
    assert 'issuer=127.0.0.1' in totpUri

    # Login without an OTP
    resp = server.request(path='/user/authentication', method='GET', basicAuth='user:password')
    # Since OTP has not been finalized, this should still succeed
    assertStatusOk(resp)

    # Finalize without an OTP
    resp = server.request(
        path='/user/%s/otp' % user['_id'], method='PUT', user=user)
    assertStatus(resp, 400)
    assert 'Girder-OTP' in resp.json['message']

    # Finalize with an invalid OTP
    resp = server.request(
        path='/user/%s/otp' % user['_id'], method='PUT', user=user,
        additionalHeaders=[('Girder-OTP', _tokenFromTotpUri(totpUri, False))])
    assertStatus(resp, 403)
    assert 'validation failed' in resp.json['message']

    # Finalize with a valid OTP
    resp = server.request(
        path='/user/%s/otp' % user['_id'], method='PUT', user=user,
        additionalHeaders=[('Girder-OTP', _tokenFromTotpUri(totpUri))])
    assertStatusOk(resp)

    # The valid token from this time period was used to finalize OTP; to prevent having to wait for
    # the next time period, flush the rateLimitBuffer
    from girder.utility._cache import rateLimitBuffer
    rateLimitBuffer.invalidate()

    # Login without an OTP
    resp = server.request(path='/user/authentication', method='GET', basicAuth='user:password')
    assertStatus(resp, 401)
    assert 'Girder-OTP' in resp.json['message']

    # Login with an invalid OTP
    resp = server.request(
        path='/user/authentication', method='GET', basicAuth='user:password',
        additionalHeaders=[('Girder-OTP', _tokenFromTotpUri(totpUri, False))])
    assertStatus(resp, 401)
    assert 'Token did not match' in resp.json['message']

    # Login with a valid OTP
    resp = server.request(
        path='/user/authentication', method='GET', basicAuth='user:password',
        additionalHeaders=[('Girder-OTP', _tokenFromTotpUri(totpUri))])
    assertStatusOk(resp)

    # Disable OTP
    resp = server.request(path='/user/%s/otp' % user['_id'], method='DELETE', user=user)
    assertStatusOk(resp)
