import datetime

from .model_base import Model
from .password import Password, genToken
from .folder import Folder
from constants import AccessType

class User(Model):
    def initialize(self):
        self.name = 'user'
        self.setIndexedFields(['login', 'email'])
        self.passwordModel = Password()
        self.folderModel = Folder()

    def refreshToken(self, user, days=180):
        """
        Generate a new token and update the provided user document.
        :param user: The user document.
        :type user: dict
        :param days: Number of days token should be valid.
        :type days: int
        :returns: The updated user document.
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
        :param admin: Whether user is global administrator.
        :type admin: bool
        :param tokenLifespan: Number of days the long-term token should last.
        :type tokenLifespan: int
        :returns: The user document that was created.
        """
        (salt, hashAlg) = self.passwordModel.encryptAndStore(password)

        # Generate a token to be used for a long-term cookie. It is up to the caller
        # to actually send the cookie to the user agent if desired.
        token = genToken()
        now = datetime.datetime.now()
        lifespan = datetime.timedelta(days=tokenLifespan)

        user = self.save({
            'login' : login,
            'email' : email,
            'firstName' : firstName,
            'lastName' : lastName,
            'salt' : salt,
            'created' : now,
            'token' : token,
            'tokenExpires' : now + lifespan,
            'hashAlg' : hashAlg,
            'emailVerified' : False,
            'admin' : admin
            })

        # Create some default folders for the user and give the user admin access to them
        publicFolder = self.folderModel.createFolder(user, 'Public', parentType='user',
                                                     public=True, creator=user)
        privateFolder = self.folderModel.createFolder(user, 'Private', parentType='user',
                                                     public=False, creator=user)
        self.folderModel.setUserAccess(publicFolder, user, AccessType.ADMIN)
        self.folderModel.setUserAccess(privateFolder, user, AccessType.ADMIN)

        user['folders'] = [publicFolder['_id'], privateFolder['_id']]

        return self.save(user)

