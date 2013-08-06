import datetime

from .model_base import Model
from constants import AccessType

class User(Model):

    def initialize(self):
        self.name = 'user'
        self.requireModels(['folder', 'password'])
        self.setIndexedFields(['login', 'email'])

    def createUser(self, login, password, firstName, lastName, email,
                   admin=False):
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

        user = self.save({
            'login' : login,
            'email' : email,
            'firstName' : firstName,
            'lastName' : lastName,
            'salt' : salt,
            'created' : datetime.datetime.now(),
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

