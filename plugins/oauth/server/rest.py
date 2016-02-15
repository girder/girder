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

import cherrypy
import datetime
import six

from girder.constants import AccessType
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException
from girder.api import access
from . import constants, providers


class OAuth(Resource):
    def __init__(self):
        super(OAuth, self).__init__()
        self.resourceName = 'oauth'

        self.route('GET', ('provider',), self.listProviders)
        self.route('GET', (':provider', 'callback'), self.callback)

    def _createStateToken(self, redirect):
        csrfToken = self.model('token').createToken(days=0.25)

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

        token = self.model('token').load(
            csrfTokenId, objectId=False, level=AccessType.READ)
        if token is None:
            raise RestException('Invalid CSRF token (state="%s").' % state,
                                code=403)

        self.model('token').remove(token)

        if token['expires'] < datetime.datetime.utcnow():
            raise RestException('Expired CSRF token (state="%s").' % state,
                                code=403)

        if not redirect:
            raise RestException('No redirect location (state="%s").' % state)

        return redirect

    @access.public
    @describeRoute(
        Description('Get the list of enabled OAuth2 providers and their URLs.')
        .notes('By default, returns an object mapping names of providers to '
               'the appropriate URL.')
        .param('redirect', 'Where the user should be redirected upon completion'
               ' of the OAuth2 flow.')
        .param('list', 'Whether to return the providers as an ordered list.',
               required=False, dataType='boolean', default=False)
    )
    def listProviders(self, params):
        self.requireParams(('redirect',), params)
        redirect = params['redirect']
        returnList = self.boolParam('list', params, default=False)

        enabledNames = self.model('setting').get(
            constants.PluginSettings.PROVIDERS_ENABLED)

        enabledProviders = [
            provider
            for providerName, provider in six.viewitems(providers.idMap)
            if providerName in enabledNames
        ]
        if enabledProviders:
            state = self._createStateToken(redirect)
        else:
            state = None

        if returnList:
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
    @describeRoute(None)
    def callback(self, provider, params):
        if 'error' in params:
            raise RestException("Provider returned error: '%s'." %
                                params['error'], code=502)

        self.requireParams(('state', 'code'), params)

        providerName = provider
        provider = providers.idMap.get(providerName)
        if not provider:
            raise RestException("Unknown provider '%s'." % providerName)

        redirect = self._validateCsrfToken(params['state'])

        providerObj = provider(cherrypy.url())
        token = providerObj.getToken(params['code'])
        user = providerObj.getUser(token)

        self.sendAuthTokenCookie(user)

        raise cherrypy.HTTPRedirect(redirect)
