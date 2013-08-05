import datetime

from . import Model
from .password import Password, genToken

class User(Model):
    def initialize(self):
        self.name = 'user'
        self.setIndexedFields(['login', 'email'])
        self.passwordModel = Password()

    def refreshToken(self, user, days=180):
        """
        Generate a new token and update the provided user document.
        @param user The user document.
        @param days Number of days token should be valid.
        """
        assert user.has_key('_id')

        user['token'] = genToken()
        user['tokenExpires'] = datetime.datetime.now() + datetime.timedelta(days=days)
        return self.save(user)

    def createUser(self, login, password, firstName, lastName, email,
                   admin=False, tokenLifespan=180):
        """
        Create a new user with the given information. The user will be created
        with the default "Public" and "Private" folders. Validation must be done
        in advance by the caller.
        @param [admin=False] Whether user is global administrator.
        @param [tokenLifespan=180] Number of days the long-term token should last.
        @return The user document that was created.
        """
        (salt, hashAlg) = self.passwordModel.encryptAndStore(password)

        # Generate a token to be used for a long-term cookie. It is up to the caller
        # to actually send the cookie to the user agent if desired.
        token = genToken()
        now = datetime.datetime.now()
        lifespan = datetime.timedelta(days=tokenLifespan)

        return self.save({
          'login' : login,
          'email' : email,
          'firstName' : firstName,
          'lastName' : lastName,
          'salt' : salt,
          'created' : now,
          'token' : token,
          'tokenExpires' : now + lifespan,
          'hashAlg' : hashAlg,
          #'folders' : [publicFolder['_id'], privateFolder['_id']],
          'emailVerified' : False,
          'admin' : admin
          })
