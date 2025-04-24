from ..describe import Description, autoDescribeRoute
from ..rest import Resource, filtermodel
from girder.api import access
from girder.exceptions import RestException
from girder.models.api_key import ApiKey as ApiKeyModel
from girder.models.setting import Setting
from girder.models.user import User
from girder.constants import AccessType
from girder.settings import SettingKey


class ApiKey(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'api_key'
        self.route('GET', (), self.listKeys)
        self.route('POST', (), self.createKey)
        self.route('POST', ('token',), self.createToken)
        self.route('PUT', (':id',), self.updateKey)
        self.route('DELETE', (':id',), self.deleteKey)

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('List API keys for a given user.')
        .notes('Only site administrators may list keys for other users. If no '
               'userId parameter is passed, lists keys for the current user.')
        .param('userId', 'ID of the user whose keys to list.', required=False)
        .pagingParams(defaultSort='name')
        .errorResponse()
    )
    def listKeys(self, userId, limit, offset, sort):
        user = self.getCurrentUser()

        if userId not in {None, str(user['_id'])}:
            self.requireAdmin(user)
            user = User().load(userId, force=True, exc=True)

        return list(ApiKeyModel().list(user, offset=offset, limit=limit, sort=sort))

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('Create a new API key.')
        .param('name', 'Name for the API key.', required=False, default='', strip=True)
        .jsonParam('scope', 'JSON list of scopes for this key.', required=False)
        .param('tokenDuration', 'Max number of days tokens created with this '
               'key will last.', required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean', default=True)
        .modelParam('targetUserId', 'Id of user to apply the key to', model=User, paramType='query',
                    level=AccessType.ADMIN, destName='targetUser', required=False)
        .errorResponse()
    )
    def createKey(self, name, scope, tokenDuration, active, targetUser):
        if Setting().get(SettingKey.API_KEYS):
            return ApiKeyModel().createApiKey(
                user=targetUser or self.getCurrentUser(),
                name=name, scope=scope, days=tokenDuration, active=active)
        else:
            raise RestException('API key functionality is disabled on this instance.')

    @access.user
    @filtermodel(ApiKeyModel)
    @autoDescribeRoute(
        Description('Update an API key.')
        .modelParam('id', 'The ID of the API key.', model=ApiKeyModel, destName='apiKey',
                    level=AccessType.WRITE)
        .param('name', 'Name for the key.', required=False, strip=True)
        .jsonParam('scope', 'JSON list of scopes for this key.', required=False,
                   default=())
        .param('tokenDuration', 'Max number of days tokens created with this key will last.',
               required=False)
        .param('active', 'Whether the key is currently active.', required=False,
               dataType='boolean')
        .errorResponse()
    )
    def updateKey(self, apiKey, name, scope, tokenDuration, active):
        if active is not None:
            apiKey['active'] = active
        if name is not None:
            apiKey['name'] = name
        if tokenDuration is not None:
            apiKey['tokenDuration'] = tokenDuration
        if scope != ():
            apiKey['scope'] = scope

        return ApiKeyModel().save(apiKey)

    @access.user
    @autoDescribeRoute(
        Description('Delete an API key.')
        .modelParam('id', 'The ID of the API key to delete.', model=ApiKeyModel,
                    level=AccessType.ADMIN, destName='apiKey')
        .errorResponse()
    )
    def deleteKey(self, apiKey):
        ApiKeyModel().remove(apiKey)
        return {'message': 'Deleted API key %s.' % apiKey['name']}

    @access.public
    @autoDescribeRoute(
        Description('Create a token from an API key.')
        .param('key', 'The API key.', strip=True)
        .param('duration', 'Number of days that the token should last.',
               required=False, dataType='float')
        .errorResponse()
    )
    def createToken(self, key, duration):
        if not Setting().get(SettingKey.API_KEYS):
            raise RestException('API key functionality is disabled on this instance.')

        user, token = ApiKeyModel().createToken(key, days=duration)

        # Return the same structure as a normal user login, except do not
        # include the full user document since the key may not authorize
        # reading user information. We also intentionally do not set the cookie
        # as we would during a normal login, in case someone is using this via swagger.
        return {
            'user': {
                '_id': user['_id']
            },
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'scope': token['scope']
            }
        }
