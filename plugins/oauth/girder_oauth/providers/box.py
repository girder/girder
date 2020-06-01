# -*- coding: utf-8 -*-
import urllib.parse

from girder.api.rest import getApiUrl
from girder.exceptions import RestException
from girder.models.setting import Setting

from .base import ProviderBase
from ..settings import PluginSettings


class Box(ProviderBase):
    _AUTH_URL = 'https://account.box.com/api/oauth2/authorize'
    _TOKEN_URL = 'https://api.box.com/oauth2/token'
    _API_USER_URL = 'https://api.box.com/2.0/users/me'

    def getClientIdSetting(self):
        return Setting().get(PluginSettings.BOX_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(PluginSettings.BOX_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(PluginSettings.BOX_CLIENT_ID)

        if not clientId:
            raise Exception('No Box client ID setting is present.')

        callbackUrl = '/'.join((getApiUrl(), 'oauth', 'box', 'callback'))

        query = urllib.parse.urlencode({
            'response_type': 'code',
            'client_id': clientId,
            'redirect_uri': callbackUrl,
            'state': state,
        })
        return '%s?%s' % (cls._AUTH_URL, query)

    def getToken(self, code):
        params = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
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
        headers = {
            'Authorization': 'Bearer %s' % token['access_token'],
            'Accept': 'application/json'
        }

        # Get user's email address
        resp = self._getJson(method='GET', url=self._API_USER_URL, headers=headers)
        email = resp.get('login')
        if not email:
            raise RestException(
                'Box did not return user information.', code=502)

        # Get user's OAuth2 ID, login, and name
        oauthId = resp.get('id')
        if not oauthId:
            raise RestException('Box did not return a user ID.', code=502)

        names = resp.get('name').split()
        firstName, lastName = names[0], names[-1]
        return self._createOrReuseUser(oauthId, email, firstName, lastName)
