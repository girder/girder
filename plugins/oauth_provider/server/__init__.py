from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.models.token import Token
from six.moves import urllib
from .client import Client
from .code import Code

class OAuthClient(Resource):
    def __init__(self):
        super(OAuthClient, self).__init__()
        self.resourceName = 'oauth_client'

        self.route('GET', (), self.listClients)
        self.route('GET', (':id',), self.getClient)
        self.route('POST', (), self.createClient)
        self.route('POST', ('token',), self.createToken)
        self.route('POST', (':id', 'authorization',), self.authorizeClient)
        self.route('PUT', (':id',), self.updateClient)
        self.route('DELETE', (':id',), self.deleteClient)

    @access.admin
    @filtermodel(Client)
    @autoDescribeRoute(
        Description('List OAuth clients.')
        .pagingParams(defaultSort='name')
    )
    def listClients(self, limit, offset, sort):
        return list(Client().find(limit=limit, offset=offset, sort=sort))

    @access.public
    @filtermodel(Client)
    @autoDescribeRoute(
        Description('Get information for an OAuth client.')
        .modelParam('id', 'The ID of the client.', model=Client, destName='client')
    )
    def getClient(self, client):
        return client

    @access.admin
    @filtermodel(Client)
    @autoDescribeRoute(
        Description('Create a new OAuth client.')
        .param('name', 'A name for this client application.')
        .jsonParam('authorizedRedirects', 'JSON array of authorized redirect URIs.',
                   schema=Client.authSchema)
        .jsonParam('authorizedOrigins', 'JSON array of authorized origins.', required=False,
                   schema=Client.authSchema, default=[])
    )
    def createClient(self, name, authorizedRedirects, authorizedOrigins):
        return Client().createClient(name, authorizedRedirects, authorizedOrigins)

    @access.admin
    @filtermodel(Client)
    @autoDescribeRoute(
        Description('Update an existing OAuth client')
        .modelParam('id', 'The ID of the client.', model=Client, destName='client')
        .param('name', 'A name for this client application.')
        .jsonParam('authorizedRedirects', 'JSON array of authorized redirect URIs.',
                   schema=Client.authSchema)
        .jsonParam('authorizedOrigins', 'JSON array of authorized origins.', required=False,
                   schema=Client.authSchema)
    )
    def updateClient(self, client, name, authorizedRedirects, authorizedOrigins):
        if name is not None:
            client['name'] = name
        if authorizedRedirects is not None:
            client['authorizedRedirects'] = authorizedRedirects
        if authorizedOrigins is not None:
            client['authorizedOrigins'] = authorizedOrigins

        return Client().save(client)

    @access.admin
    @autoDescribeRoute(
        Description('Delete an OAuth client.')
        .modelParam('id', 'The ID of the client.', model=Client, destName='client')
    )
    def deleteClient(self, client):
        Client().remove(client)

    @access.user
    @autoDescribeRoute(
        Description('Authorize an OAuth client.')
        .modelParam('id', 'The ID of the client.', model=Client, destName='client')
        .param('authorize', 'Whether or not to accept the authorization.', dataType='boolean')
        .param('redirect', 'The redirect URI.')
        .param('state', 'The state parameter to pass back to the client.', required=False)
        .param('scope', 'The scope of authorization as a space-separated list of scope IDs.')
    )
    def authorizeClient(self, authorize, client, redirect, scope, state):
        def mkresp(params):
            if state is not None:
                params['state'] = state

            return {'url': '%s?%s' % (redirect, urllib.parse.urlencode(params))}

        if redirect not in client['authorizedRedirects']:
            return mkresp({
                'error': 'The redirect URI "%s" is not allowed by this client.' % redirect
            })

        if not authorize:
            return mkresp({
                'error': 'The user declined to authorize this client.'
            })

        return mkresp({
            'code': Code().createCode(client, scope, self.getCurrentUser())['code']
        })

    @access.public
    @autoDescribeRoute(
        Description('Get an auth token from a client access code.')
        .modelParam('clientId', 'The ID of the client making this request.', model=Client,
                    destName='client', paramType='formData')
        .param('code', 'The client access code obtained from the authorization flow.')
        .param('redirect', 'The redirect URI of this client.')
        .param('secret', 'The secret for this client.')
    )
    def createToken(self, code, client, redirect, secret):
        return {'token': Code().createToken(code, client, redirect, secret)['_id']}


def load(info):
    info['apiRoot'].oauth_client = OAuthClient()

    Token().ensureIndex('oauthClientId')
