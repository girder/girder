import cherrypy
import json

from ..rest import Resource, RestException

COOKIE_LIFETIME = cherrypy.config['sessions']['cookie_lifetime']

class User(Resource):

    def initialize(self):
        self.requireModels(['password', 'token', 'user'])

    def _filter(self, user):
        """
        Helper to filter the user model.
        """
        return self.filterDocument(user, allow=['_id', 'login', 'email', 'public', 'size',
                                                'firstName', 'lastName', 'admin', 'hashAlg'])

    def _sendAuthTokenCookie(self, user, token):
        """ Helper method to send the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['authToken'] = json.dumps({
            'userId' : str(user['_id']),
            'token' : str(token['_id'])
            })
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = COOKIE_LIFETIME * 3600 * 24

    def _deleteAuthTokenCookie(self):
        """ Helper method to kill the authentication cookie """
        cookie = cherrypy.response.cookie
        cookie['authToken'] = ''
        cookie['authToken']['path'] = '/'
        cookie['authToken']['expires'] = 0

    def index(self, params):
        return 'todo: index'

    def login(self, params):
        """
        Login endpoint. Sends a session cookie in the response on success.
        :param login: The login name.
        :param password: The user's password.
        """
        self.requireParams(['login', 'password'], params)

        login = params['login'].lower().strip()
        loginField = 'email' if '@' in login else 'login'

        cursor = self.userModel.find({loginField : login}, limit=1)
        if cursor.count() == 0:
            raise RestException('Login failed.', code=403)

        user = cursor.next()

        token = self.tokenModel.createToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user, token)

        if not self.passwordModel.authenticate(user, params['password']):
            raise RestException('Login failed.', code=403)

        return {'message' : 'Login succeeded.',
                'authToken' : {
                    'token' : token['_id'],
                    'expires' : token['expires'],
                    'userId' : user['_id']
                    }
                }

    def logout(self):
        self._deleteAuthTokenCookie()
        return {'message' : 'Logged out.'}

    def register(self, params):
        self.requireParams(['firstName', 'lastName', 'login', 'password', 'email'], params)

        user = self.userModel.createUser(login=params['login'],
                                         password=params['password'],
                                         email=params['email'],
                                         firstName=params['firstName'],
                                         lastName=params['lastName'])

        token = self.tokenModel.createToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user, token)

        return self._filter(user)

    @Resource.endpoint
    def GET(self, path, params):
        if not path:
            return self.index(params)
        else: # assume it's a user id
            user = self.getCurrentUser()
            return self._filter(self.getObjectById(self.userModel, id=path[0],
                                                   user=user, checkAccess=True))

    @Resource.endpoint
    def POST(self, path, params):
        """
        Use this endpoint to register a new user, to login, or to logout.
        """
        if not path:
            return self.register(params)
        elif path[0] == 'login':
            return self.login(params)
        elif path[0] == 'logout':
            return self.logout()
        else:
            raise RestException('Unsupported operation.')
