import cherrypy
import json
import re

from ..rest import Resource, RestException

COOKIE_LIFETIME = cherrypy.config['sessions']['cookie_lifetime']

class User(Resource):

    def initialize(self):
        self.requireModels(['password', 'token', 'user'])

    def _filter(self, user):
        """
        Helper to filter the user model.
        """
        # TODO stub
        return user

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
        cursor = self.userModel.find({'login' : params['login']}, limit=1)
        if cursor.count() == 0:
            raise RestException('Login failed.', code=403)

        user = cursor.next()

        token = self.tokenModel.createToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user, token)

        if not self.passwordModel.authenticate(user, params['password']):
            raise RestException('Login failed.', code=403)

        return {'message' : 'Login succeeded.'}

    def logout(self):
        self._deleteAuthTokenCookie()
        return {'message' : 'Logged out.'}

    def register(self, params):
        self.requireParams(['firstName', 'lastName', 'login', 'password', 'email'], params)

        login = params['login'].lower()
        email = params['email'].lower()

        if len(params['password']) < 6:
            raise RestException('Password must be at least 6 characters.', extra={
                'fields' : ['password']
                })

        if not re.match(cherrypy.config['users']['email_regex'], email):
            raise RestException('Invalid email address.', extra={
                'fields' : ['email']
                })

        existing = self.userModel.find({'login' : login}, limit=1)
        if existing.count(True) > 0:
            raise RestException('That login is already registered.', extra={
                'fields' : ['login']
                })

        existing = self.userModel.find({'email' : email}, limit=1)
        if existing.count(True) > 0:
            raise RestException('That email is already registered.', extra={
                'fields' : ['email']
                })

        user = self.userModel.createUser(login=login,
                                         password=params['password'],
                                         email=email,
                                         firstName=params['firstName'],
                                         lastName=params['lastName'])

        token = self.tokenModel.createToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user, token)

        return self._filter(user)

    @Resource.endpoint
    def GET(self, pathParam=None, **params):
        if pathParam is None:
            return self.index(params)
        else: # assume it's a user id
            user = self.getCurrentUser()
            return self._filter(self.getObjectById(self.userModel, id=pathParam,
                                                   user=user, checkAccess=True))

    @Resource.endpoint
    def POST(self, pathParam=None, **params):
        """
        Use this endpoint to register a new user, to login, or to logout.
        """
        if pathParam is None:
            return self.register(params)
        elif pathParam == 'login':
            return self.login(params)
        elif pathParam == 'logout':
            return self.logout()
        else:
            raise RestException('Unsupported operation')
