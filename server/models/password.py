import cherrypy
import hashlib
import random
import string

from . import Model

auth_cfg = cherrypy.config['auth']
HASH_ALG = auth_cfg['hash_alg']

class Password(Model):
    def initialize(self):
        self.name = 'password'

    def _digest(self, alg, password, salt=False):
        """
        Helper method to perform the password digest.
        @param alg The hash algorithm to use (sha512 | bcrypt)
        @param password The password to digest
        @param The salt to use. In the case of bcrypt,
               when storing the password, pass False;
               when testing the password, pass the hashed value.
        """
        if alg == 'sha512':
            return hashlib.sha512(password + salt).hexdigest()
        elif alg == 'bcrypt':
            try:
                import bcrypt
            except ImportError:
                raise Exception('Bcrypt module is not installed. See local.auth.cfg.')

            if salt == False:
                return bcrypt.hashpw(password, bcrypt.gensalt())
            else:
                return bcrypt.hashpw(password, salt)
        else:
            raise Exception('Unsupported hash algorithm: %s' % alg)

    def authenticate(self, user, password):
        """
        Authenticate a user.
        @param user The user document.
        @param password The attempted password.
        @return True or False: whether authentication succeeded.
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
        Generates a random salt and stores the given password with it.
        @param password The password to encrypt and store.
        @return The salt that was used.
        """
        if type(password) is unicode:
            password = password.encode('utf-8')

        if HASH_ALG == 'bcrypt':
            """
            With bcrypt, we actually need the one-to-one correspondence of
            hashed password to user, so we store it as the salt entry in
            the user table.
            """
            salt = self._digest(alg=HASH_ALG, password=password)
        else:
            """
            With other hashing algorithms, we store the salt with the user
            and store the hashed value in a separate table with no
            correspondence to the user.
            """
            salt = ''.join(random.choice(string.letters + string.digits) for x in range(64))
            hash = self._digest(salt=salt, alg=HASH_ALG, password=password)
            self.save({'_id' : hash})

        return (salt, HASH_ALG)
