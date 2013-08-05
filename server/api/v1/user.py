import re

from ..rest import Resource, RestException
from models import user as userModel, password as passwordModel

class User(Resource):

    def __init__(self):
        self.userModel = userModel.User()
        self.passwordModel = passwordModel.Password()

    def index(self, params):
        return 'todo: index'

    def login(self, params):
        self.requireParams(['login', 'password'], params)
        cursor = self.userModel.find({'login' : params['login']}, limit=1)
        if cursor.count() == 0:
            raise RestException('Login failed', code=403)

        user = cursor.next()

        if not self.passwordModel.authenticate(user, params['password']):
            raise RestException('Login failed', code=403)

        # TODO create session vars

        return {'message' : 'Login succeeded'}

    def logout(self, params):
        return 'todo: logout'

    def register(self, params):
        self.requireParams(['firstName', 'lastName', 'login', 'password', 'email'], params)

        login = params['login'].lower()
        email = params['email'].lower()

        if len(params['password']) < 6:
            raise RestException('Password must be at least 6 characters.', extra={
                'fields' : ['password']
                })

        if not re.match("[\w\.\-]*@[\w\.\-]*\.\w+", email):
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

        return self.userModel.createUser(login=login,
                                         password=params['password'],
                                         email=email,
                                         firstName=params['firstName'],
                                         lastName=params['lastName'])

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
            return self.logout(params)
        else:
            raise RestException('Unsupported operation')


