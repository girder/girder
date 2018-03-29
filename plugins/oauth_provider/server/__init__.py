from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from .client import Client

class OAuthClient(Resource):
    def __init__(self):
        super(OAuthClient, self).__init__()
        self.resourceName = 'oauth_client'

        self.route('GET', (), self.listClients)
        self.route('GET', (':id',), self.getClient)
        self.route('POST', (), self.createClient)
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


def load(info):
    info['apiRoot'].oauth_client = OAuthClient()
