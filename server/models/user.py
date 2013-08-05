from . import Model
from .password import Password

class User(Model):
    def initialize(self):
        self.name = 'user'
        self.setIndexedFields(['login', 'email'])
        self.passwordModel = Password()


    def createUser(self, login, password, firstName, lastName, email):
        """
        Create a new user with the given information. The user will be created
        with the default "Public" and "Private" folders. Validation must be done
        in advance by the caller.
        @return The user document that was created.
        """
        (salt, hashAlg) = self.passwordModel.encryptAndStore(password)

        return self.save({
          'login' : login,
          'email' : email,
          'firstName' : firstName,
          'lastName' : lastName,
          'salt' : salt,
          'hashAlg' : hashAlg,
          #'folders' : [publicFolder['_id'], privateFolder['_id']],
          'emailVerified' : False
          })
