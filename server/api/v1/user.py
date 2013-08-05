import cherrypy
import json
import re

from ..rest import Resource, RestException
from models import user as userModel, password as passwordModel

COOKIE_LIFETIME = cherrypy.config['sessions']['cookie_lifetime']

class User(Resource):

    def __init__(self):
        self.userModel = userModel.User()
        self.passwordModel = passwordModel.Password()

    def _sendAuthTokenCookie(self, user):
        """ Helper method to send the long-term authentication token """
        cookie = cherrypy.response.cookie
        cookie['auth_token'] = json.dumps({
            '_id' : str(user['_id']),
            'token' : user['token']
            })
        cookie['auth_token']['path'] = '/'
        cookie['auth_token']['expires'] = COOKIE_LIFETIME * 3600 * 24

    def _deleteAuthTokenCookie(self):
        """ Helper method to kill the long-term authentication token """
        cookie = cherrypy.response.cookie
        cookie['auth_token'] = ''
        cookie['auth_token']['path'] = '/'
        cookie['auth_token']['expires'] = 0

    def index(self, params):
        return 'todo: index'

    def login(self, params):
        """
        Login endpoint (user/login). Creates sessions and cookies.
        @param login The login name.
        @param password The user's password
        """
        self.requireParams(['login', 'password'], params)
        cursor = self.userModel.find({'login' : params['login']}, limit=1)
        if cursor.count() == 0:
            raise RestException('Login failed.', code=403)

        user = cursor.next()

        # TODO condition this on "remember me" option?
        user = self.userModel.refreshToken(user, days=COOKIE_LIFETIME)
        self._sendAuthTokenCookie(user)

        if not self.passwordModel.authenticate(user, params['password']):
            raise RestException('Login failed.', code=403)

        cherrypy.session.acquire_lock()
        cherrypy.session['user'] = user
        cherrypy.session.release_lock()

        return {'message' : 'Login succeeded.'}

    def logout(self):
        cherrypy.session.acquire_lock()
        cherrypy.session.clear()
        cherrypy.session.release_lock()

        cherrypy.lib.sessions.expire()

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
                                         lastName=params['lastName'],
                                         tokenLifespan=COOKIE_LIFETIME)

        # TODO possibly condition this on a "remember me" value?
        self._sendAuthTokenCookie(user)

        cherrypy.session.acquire_lock()
        cherrypy.session['user'] = user
        cherrypy.session.release_lock()

        return user

    @Resource.endpoint
    def GET(self, pathParam=None, **params):
        if pathParam is None:
            return self.index(params)
        else: # assume it's a user id
            return self.getObjectById(self.userModel, pathParam)

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
