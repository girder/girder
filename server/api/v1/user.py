import re

from ..rest import Resource, RestException
from models import user as userModel

class User(Resource):

    def __init__(self):
        self.model = userModel.User()

    @Resource.endpoint
    def GET(self, id=None):
        #TODO
        return {'id': id}

    @Resource.endpoint
    def POST(self, **params):
        """
        Use this endpoint to register a new user.
        """
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

        existing = self.model.find({'login' : login}, limit=1)
        if existing.count() > 0:
            raise RestException('That login is already registered.', extra={
                'fields' : ['login']
                })

        existing = self.model.find({'email' : email}, limit=1)
        if existing.count() > 0:
            raise RestException('That email is already registered.', extra={
                'fields' : ['email']
                })

        return self.model.createUser(login=login,
                                     password=params['password'],
                                     email=email,
                                     firstName=params['firstName'],
                                     lastName=params['lastName'])
