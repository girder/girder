import hashlib
import random
import string

from . import Model

HASH_ALG = 'sha512'

class Password(Model):
    def initialize(self):
        self.name = 'password'

    def _digest(self, salt, alg, password):
        """
        Helper method to perform the password digest.
        """
        if alg == 'sha512':
            return hashlib.sha512(password + salt).hexdigest()
        else:
            raise Exception('Unsupported hash algorithm: %s' % alg)

    def authenticate(self, user, password):
        """
        Authenticate a user.
        @param user The user document.
        @param password The attempted password.
        @return True or False: whether authentication succeeded.
        """
        match = self.load(self._digest(user['salt'], user['hashAlg'], password), False)
        return match is not None

    def encryptAndStore(self, password):
        """
        Generates a random salt and stores the given password with it.
        @param password The password to encrypt and store.
        @return The salt that was used.
        """
        salt = ''.join(random.choice(string.letters + string.digits) for x in range(64))

        self.save({'_id' : self._digest(salt, HASH_ALG, password)})
        return (salt, HASH_ALG)
