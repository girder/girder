#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import hashlib
import re
import six

from girder import events
from girder.exceptions import ValidationException
from girder.utility import config
from .model_base import Model
from .token import genToken


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
        cur_config = config.getConfig()
        if alg == 'sha512':
            return hashlib.sha512((password + salt).encode('utf8')).hexdigest()
        elif alg == 'bcrypt':
            try:
                import bcrypt
            except ImportError:
                raise Exception(
                    'Bcrypt module is not installed. See girder.local.cfg.')

            password = password.encode('utf8')

            if salt is None:
                rounds = int(cur_config['auth']['bcrypt_rounds'])
                return bcrypt.hashpw(password, bcrypt.gensalt(rounds))
            else:
                if isinstance(salt, six.text_type):
                    salt = salt.encode('utf8')
                return bcrypt.hashpw(password, salt)
        else:
            raise Exception('Unsupported hash algorithm: %s' % alg)

    def validate(self, doc):
        if not doc.get('_id', ''):
            # Internal error, this should not happen
            raise Exception('Attempting to store empty password.')

        return doc

    def hasPassword(self, user):
        """
        Returns whether or not the given user has a password stored in the
        database. If not, it is expected that the user will be authenticated by
        an external service.

        :param user: The user to test.
        :type user: dict
        :returns: bool
        """
        return 'hashAlg' in user

    def authenticate(self, user, password):
        """
        Authenticate a user.

        :param user: The user document.
        :type user: dict
        :param password: The attempted password.
        :type password: str
        :returns: Whether authentication succeeded (bool).
        """
        if not self.hasPassword(user):
            e = events.trigger('no_password_login_attempt', {
                'user': user,
                'password': password
            })

            if len(e.responses):
                return e.responses[-1]

            raise ValidationException(
                'This user does not have a password. You must log in with an '
                'external service, or reset your password.')

        hash = self._digest(salt=user['salt'], alg=user['hashAlg'],
                            password=password)

        if user['hashAlg'] == 'bcrypt':
            if isinstance(user['salt'], six.text_type):
                user['salt'] = user['salt'].encode('utf8')
            return hash == user['salt']
        else:
            return self.load(hash, False) is not None

    def encryptAndStore(self, password):
        """
        Encrypt and store the given password. The exact internal details and
        mechanisms used for storage are abstracted away, but the guarantee is
        made that once this method is called on a password and the returned salt
        and algorithm are stored with the user document, calling
        Password.authenticate() with that user document and the same password
        will return True.

        :param password: The password to encrypt and store.
        :type password: str
        :returns: {tuple} (salt, hashAlg) The salt to store with the
                  user document and the algorithm used for secure
                  storage. Both should be stored in the corresponding
                  user document as 'salt' and 'hashAlg' respectively.
        """
        cur_config = config.getConfig()

        # Normally this would go in validate() but password is a special case.
        if not re.match(cur_config['users']['password_regex'], password):
            raise ValidationException(
                cur_config['users']['password_description'], 'password')

        alg = cherrypy.config['auth']['hash_alg']
        if alg == 'bcrypt':
            """
            With bcrypt, we actually need the one-to-one correspondence of
            hashed password to user, so we store the hash as the salt entry in
            the user table.
            """
            salt = self._digest(alg=alg, password=password)
        else:
            """
            With other hashing algorithms, we store the salt with the user
            and store the hashed value in a separate table with no
            correspondence to the user.
            """
            salt = genToken()
            hash = self._digest(salt=salt, alg=alg, password=password)
            self.save({'_id': hash})

        return salt, alg
