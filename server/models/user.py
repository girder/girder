from . import Model

class User(Model):
    def initialize(self):
        self.name = 'user'

    def createUser(self, login, password, firstName, lastName, email):
        # TODO salting and bcrypt and stuff
        return self.save({
          'login' : login,
          'email' : email,
          'firstName' : firstName,
          'lastName' : lastName,
          'emailVerified' : False
          })
