import cherrypy
import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from girder import events
from girder.constants import AccessType
from girder.exceptions import RestException
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.api import access
from girder.models.setting import Setting
from girder.models.user import User
from girder.models.token import Token

from . import providers
from .settings import PluginSettings


class OAuth(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'oauth'

        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', (':provider', 'callback'), self.callback)

    def _createStateToken(self, redirect):
        csrfToken = Token().createToken(days=0.25)

        # The delimiter is arbitrary, but a dot doesn't need to be URL-encoded
        state = '%s.%s' % (csrfToken['_id'], redirect)
        return state

    def _validateCsrfToken(self, state):
        """
        Tests the CSRF token value in the cookie to authenticate the user as
        the originator of the OAuth2 login. Raises a RestException if the token
        is invalid.
        """
        csrfTokenId, _, redirect = state.partition('.')

        token = Token().load(csrfTokenId, objectId=False, level=AccessType.READ)
        if token is None:
            raise RestException('Invalid CSRF token (state="%s").' % state, code=403)

        Token().remove(token)

        if token['expires'] < datetime.datetime.now(datetime.timezone.utc):
            raise RestException('Expired CSRF token (state="%s").' % state,
                                code=403)

        if not redirect:
            raise RestException('No redirect location (state="%s").' % state)

        return redirect

    @access.public
    @autoDescribeRoute(
        Description('Get the list of enabled OAuth2 providers and their URLs.')
        .notes('By default, returns an object mapping names of providers to '
               'the appropriate URL.')
        .param('redirect', 'Where the user should be redirected upon completion'
               ' of the OAuth2 flow.')
        .param('list', 'Whether to return the providers as an ordered list.',
               required=False, dataType='boolean', default=False)
    )
    def listProviders(self, redirect, list):
        enabledNames = Setting().get(PluginSettings.PROVIDERS_ENABLED)

        enabledProviders = [
            provider
            for providerName, provider in providers.idMap.items()
            if providerName in enabledNames
        ]
        if enabledProviders:
            state = self._createStateToken(redirect)
        else:
            state = None

        if list:
            return [
                {
                    'id': provider.getProviderName(external=False),
                    'name': provider.getProviderName(external=True),
                    'url': provider.getUrl(state)
                }
                for provider in enabledProviders
            ]
        else:
            return {
                provider.getProviderName(external=True): provider.getUrl(state)
                for provider in enabledProviders
            }

    @access.public
    @autoDescribeRoute(
        Description('Callback called by OAuth providers.')
        .param('provider', 'The provider name.', paramType='path')
        .param('state', 'Opaque state string.', required=False)
        .param('code', 'Authorization code from provider.', required=False)
        .param('error', 'Error message from provider.', required=False),
        hide=True
    )
    def callback(self, provider, state, code, error):
        if error is not None:
            raise RestException("Provider returned error: '%s'." % error, code=502)

        self.requireParams({'state': state, 'code': code})

        providerName = provider
        provider = providers.idMap.get(providerName)
        if not provider:
            raise RestException('Unknown provider "%s".' % providerName)

        redirect = self._validateCsrfToken(state)

        providerObj = provider(cherrypy.url())
        token = providerObj.getToken(code)

        event = events.trigger('oauth.auth_callback.before', {
            'provider': provider,
            'token': token
        })
        if event.defaultPrevented:
            raise cherrypy.HTTPRedirect(redirect)

        user = providerObj.getUser(token)
        User().verifyLogin(user)

        event = events.trigger('oauth.auth_callback.after', {
            'provider': provider,
            'token': token,
            'user': user
        })
        if event.defaultPrevented:
            raise cherrypy.HTTPRedirect(redirect)

        token = Token().createToken(user)
        token_id = str(token['_id'])

        # Set `girderToken` in the query params of the redirect URL
        parsed = urlparse(redirect)
        query_params = parse_qs(parsed.query)
        query_params['girderToken'] = token_id
        encoded_query_params = urlencode(query_params)
        updated_redirect = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            encoded_query_params,
            parsed.fragment,
        ))

        # The cookie is still used for e.g. file downloads. Send it from the server
        # to support HttpOnly usage.
        self.sendAuthTokenCookie(token=token)

        raise cherrypy.HTTPRedirect(updated_redirect)
