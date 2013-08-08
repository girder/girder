import cherrypy
import datetime
import hashlib
import random
import string

from constants import AccessType
from .model_base import AccessControlledModel

def genToken(length=64):
    """
    Use this utility function to generate a random string of
    a desired length.
    """
    return ''.join(random.choice(string.letters + string.digits) for x in range(length))

class Token(AccessControlledModel):
    """
    This model stores session tokens for user authentication.
    """
    def initialize(self):
        self.name = 'token'

    def validate(self, doc):
        return doc

    def cleanExpired(self):
        # TODO
        pass

    def createToken(self, user, days=180):
        """
        Creates a new token for the user.
        :param user: The user to create the session for.
        :type user: dict
        :param days: The lifespan of the session in days.
        :type days: int
        :returns: The token document that was created.
        """
        token = {
            '_id' : genToken(),
            'expires' : datetime.datetime.now() + datetime.timedelta(days=days)
            }
        token = self.setUserAccess(token, user=user, level=AccessType.ADMIN, save=False)
        return self.save(token)

