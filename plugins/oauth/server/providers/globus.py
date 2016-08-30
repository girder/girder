#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import struct
import jwt
from jwt.utils import base64url_decode
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from six.moves import urllib
from six import string_types

from girder.api.rest import getApiUrl, RestException
from .base import ProviderBase
from .. import constants


class Globus(ProviderBase):
    _AUTH_URL = 'https://auth.globus.org/v2/oauth2/authorize'
    _AUTH_SCOPES = ('urn:globus:auth:scope:auth.globus.org:view_identities',
                    'openid', 'profile', 'email')
    _TOKEN_URL = 'https://auth.globus.org/v2/oauth2/token'
    _JWK_KEY_URL = 'https://auth.globus.org/jwk.json'
    jwk_keys = None

    def getClientIdSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GLOBUS_CLIENT_ID)

    def getClientSecretSetting(self):
        return self.model('setting').get(
            constants.PluginSettings.GLOBUS_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = cls.model('setting').get(
            constants.PluginSettings.GLOBUS_CLIENT_ID)

        if clientId is None:
            raise Exception('No Globus client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'globus', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': ' '.join(cls._AUTH_SCOPES)
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'redirect_uri': self.redirectUri
        }
        resp = self._getJson(method='POST', url=self._TOKEN_URL,
                             data=params,
                             headers={'Accept': 'application/json'})
        if 'error' in resp:
            raise RestException(
                'Got an error exchanging token from provider: "%s".' % resp,
                code=502)
        return resp

    def getUser(self, token):
        id_token = token.get('id_token')

        if self.jwk_keys is None:
            # Get public keys required for decoding 'id_token'
            self.jwk_keys = self._getJson(method='GET', url=self._JWK_KEY_URL)

        # There should be only one entry
        keyobj = self.jwk_keys['keys'][0]

        # Borrowed from 'cryptography' for py2 backward compat
        def decode_value(val):
            if hasattr(int, 'from_bytes'):
                int_from_bytes = int.from_bytes
            else:
                def int_from_bytes(data, byteorder, signed=False):
                    assert byteorder == 'big'
                    assert not signed

                    if len(data) % 4 != 0:
                        data = (b'\x00' * (4 - (len(data) % 4))) + data

                    result = 0

                    while len(data) > 0:
                        digit, = struct.unpack('>I', data[:4])
                        result = (result << 32) + digit
                        data = data[4:]
                    return result

            if isinstance(val, string_types):
                val = val.encode('utf-8')
            decoded = base64url_decode(val)
            return int_from_bytes(decoded, 'big')

        # Create RSA key from JSON spec
        key = rsa.RSAPublicNumbers(
            n=decode_value(keyobj['n']),
            e=decode_value(keyobj['e'])
        ).public_key(default_backend())

        # Decode 'id_token'
        # BEWARE: leeway should be 0, but upstream server seems to be desynch
        identity = jwt.decode(
            id_token, key, algorithm='RS512', leeway=100,
            audience=self.clientId)

        oauthId = identity.get('sub')
        if not oauthId:
            raise RestException(
                'Globus identity did not return a valid ID.', code=502)

        email = identity.get('email')
        if not email:
            raise RestException(
                'Globus identity did not return a valid email.', code=502)

        name = identity['name'].split()
        firstName = name[0]
        lastName = name[-1]

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
