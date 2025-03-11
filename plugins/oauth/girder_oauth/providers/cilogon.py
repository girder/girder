import warnings

from girder.api.rest import getApiUrl
from girder.exceptions import RestException
from girder.models.setting import Setting

from ..settings import PluginSettings
from .base import ProviderBase
import requests


class CILogon(ProviderBase):
    _AUTH_SCOPES = ['openid', 'email', 'profile']
    _API_USER_URL = 'https://cilogon.org/oauth2/userinfo'
    _AUTHORITY = 'https://cilogon.org'

    def getClientIdSetting(self):
        return Setting().get(PluginSettings.CILOGON_CLIENT_ID)

    def getClientSecretSetting(self):
        return Setting().get(PluginSettings.CILOGON_CLIENT_SECRET)

    @classmethod
    def getUrl(cls, state):
        clientId = Setting().get(PluginSettings.CILOGON_CLIENT_ID)
        if not clientId:
            raise Exception('No CILogon client ID setting is present.')

        redirectUri = '/'.join((getApiUrl(), 'oauth', 'cilogon', 'callback'))

        url = (
            f'{cls._AUTHORITY}/authorize'
            f'?client_id={clientId}'
            f'&response_type=code'
            f'&scope={" ".join(cls._AUTH_SCOPES)}'
            f'&redirect_uri={redirectUri}'
            f'&state={state}'
        )
        return url

    def getToken(self, code):
        clientId = self.getClientIdSetting()
        clientSecret = self.getClientSecretSetting()
        redirectUri = '/'.join((getApiUrl(), 'oauth', 'cilogon', 'callback'))

        if not clientId or not clientSecret or not redirectUri:
            raise Exception('CILogon settings are incomplete.')

        token_url = f'{self._AUTHORITY}/oauth2/token'
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirectUri,
            'client_id': clientId,
            'client_secret': clientSecret,
        }
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            response = requests.post(token_url, data=data)

        if response.status_code != 200:
            raise Exception('Error acquiring token: %s' %
                            response.json().get('error_description', 'Unknown error'))

        return response.json()

    def getUser(self, token):
        headers = {
            'Authorization': f'Bearer {token["access_token"]}',
            'Accept': 'application/json'
        }

        # Get user's info
        resp = requests.get(self._API_USER_URL, headers=headers)
        if resp.status_code != 200:
            raise RestException('Failed to fetch user info from CILogon.', code=502)

        user_data = resp.json()
        oauthId = user_data.get('sub')
        if not oauthId:
            raise RestException('CILogon did not return user ID.', code=502)

        email = user_data.get('email')
        if not email:
            raise RestException('CILogon user has no registered email address.', code=502)

        firstName = user_data.get('given_name', '')
        lastName = user_data.get('family_name', '')

        user = self._createOrReuseUser(oauthId, email, firstName, lastName)
        return user
