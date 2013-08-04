from . import Model

class User(Model):
    def initialize(self):
        self.name = 'user'

    def createUser(self, login, password, firstName, lastName):
        # TODO salting and bcrypt and stuff
        return self.save({
          'login' : login,
          'firstName' : firstName,
          'lastName' : lastName
          })
