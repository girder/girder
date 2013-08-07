import cherrypy
import hashlib
import random
import string

from .model_base import Model
from .token import genToken

auth_cfg = cherrypy.config['auth']
HASH_ALG = auth_cfg['hash_alg']

class Password(Model):
    """
    This model deals with managing user passwords.
    """
    def initialize(self):
        self.name = 'password'

    def _digest(self, alg, password, salt=None):
        """
        Helper method to perform the password digest.
        :param alg: The hash algorithm to use.
        :type alg: str - 'sha512' | 'bcrypt'
        :param password: The password to digest.
        :type password: str
        :param salt: The salt to use. In the case of bcrypt,
                     when storing the password, pass None;
                     when testing the password, pass the hashed value.
        :type salt: None or str
        :returns: The hashed value as a string.
        """
        if alg == 'sha512':
            return hashlib.sha512(password + salt).hexdigest()
        elif alg == 'bcrypt':
            try:
                import bcrypt
            except ImportError:
                raise Exception('Bcrypt module is not installed. See local.auth.cfg.')

            if salt is None:
                assert type(auth_cfg['bcrypt_rounds']) is int
                return bcrypt.hashpw(password, bcrypt.gensalt(auth_cfg['bcrypt_rounds']))
            else:
                return bcrypt.hashpw(password, salt)
        else:
            raise Exception('Unsupported hash algorithm: %s' % alg)

    def authenticate(self, user, password):
        """
        Authenticate a user.
        :param user: The user document.
        :type user: dict
        :param password: The attempted password.
        :type password: str
        :returns: Whether authentication succeeded (bool).
        """
        if type(password) is unicode:
            password = password.encode('utf-8')
        if type(user['salt']) is unicode:
            user['salt'] = user['salt'].encode('utf-8')

        hash = self._digest(salt=user['salt'], alg=user['hashAlg'], password=password)

        if user['hashAlg'] == 'bcrypt':
            return hash == user['salt']
        else:
            return self.load(hash, False) is not None

    def encryptAndStore(self, password):
        """
        Encrypt and store the given password. The exact internal details and
        mechanisms used for storage are abstracted away, but the guarantee is made that
        once this method is called on a password and the returned salt and algorithm are
        stored with the user document, calling Password.authenticate() with that user
        document and the same password will return True.
        :param password: The password to encrypt and store.
        :type password: str
        :returns: {tuple} (salt, hashAlg) The salt to store with the user document
                                          and the algorithm used for secure storage.
                                          Both should be stored in the corresponding user
                                          document as 'salt' and 'hashAlg', respectively.
        """
        if type(password) is unicode:
            password = password.encode('utf-8')

        if HASH_ALG == 'bcrypt':
            """
            With bcrypt, we actually need the one-to-one correspondence of
            hashed password to user, so we store the hash as the salt entry in
            the user table.
            """
            salt = self._digest(alg=HASH_ALG, password=password)
        else:
            """
            With other hashing algorithms, we store the salt with the user
            and store the hashed value in a separate table with no
            correspondence to the user.
            """
            salt = genToken()
            hash = self._digest(salt=salt, alg=HASH_ALG, password=password)
            self.save({'_id' : hash})

        return (salt, HASH_ALG)
