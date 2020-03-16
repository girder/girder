# -*- coding: utf-8 -*-
from six.moves import urllib

import jwt

from girder.api.rest import getApiUrl
from girder.exceptions import RestException
from girder.models.setting import Setting

from .base import ProviderBase
from ..settings import PluginSettings
import json
import base64


class Synapse(ProviderBase):
    # https://docs.synapse.org/articles/using_synapse_as_an_oauth_server.html
    _AUTH_URL = 'https://signin.synapse.org'
    _AUTH_SCOPES = []
    _TOKEN_URL = 'https://repo-prod.prod.sagebase.org/auth/v1/oauth2/token'
    _DISCOVERY_URL = 'https://repo-prod.prod.sagebase.org/auth/v1/.well-known/openid-configuration'

    def getClientIdSetting(self):
        return Setting().get(PluginSettings.SYNAPSE_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(PluginSettings.SYNAPSE_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(PluginSettings.SYNAPSE_CLIENT_ID)
        if not clientId:
            raise Exception('No Synapse client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'synapse', 'callback'))

        #OIDC claims. The complete list is here: 
        #https://rest-docs.synapse.org/rest/org/sagebionetworks/repo/model/oauth/OIDCClaimName.html
        claims = {
            'email': None,
            'given_name': None,
            'family_name': None
            }
        tokenAndUserInfoClaims = {'id_token': claims, 'userinfo': claims}

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'access_type': 'online',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
            'scope': 'openid %s' % ' '.join(cls._AUTH_SCOPES),
            'claims': json.dumps(tokenAndUserInfoClaims)
            # Synapse supports a 'nonce', but does not require it, and Girder's particular checks
            # and invalidation of the 'state' token provides the same security guarantees
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirectUri
        }
        basicAuth = ':'.join((str(self.clientId), str(self.clientSecret)))
        auth = base64.b64encode(basicAuth.encode('utf8'))
        resp = self._getJson(method='POST', url=self._TOKEN_URL, 
            data=params, headers={'Authorization': 'Basic %s' % auth.decode()})
        return resp

    def getUser(self, token):
        idToken = token['id_token']

        # Because the token came directly from Synapse's API, we don't need to verify it
        payload = jwt.decode(idToken, verify=False)

        oauthId = payload['sub']

        email = payload.get('email')
        if not email:
            raise RestException('Email address is missing.', code=502)

        discovery = self._getJson(method='GET', url=self._DISCOVERY_URL)
        userinfoUrl = discovery['userinfo_endpoint']

        userinfo = self._getJson(method='GET', url=userinfoUrl, headers={
            'Authorization': 'Bearer %s' % (token['access_token'])
        })
        firstName = userinfo.get('given_name', '')
        lastName = userinfo.get('family_name', '')

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
