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
import datetime
import re

from .model_base import AccessControlledModel, ValidationException
from girder.constants import AccessType


class User(AccessControlledModel):

    def initialize(self):
        self.name = 'user'
        self.requireModels(['folder', 'password'])
        self.ensureIndices(['login', 'email'])

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        doc['login'] = doc.get('login', '').lower().strip()
        doc['email'] = doc.get('email', '').lower().strip()
        doc['fname'] = doc.get('firstName', '').strip()
        doc['lname'] = doc.get('lastName', '').strip()

        if not doc.get('salt', ''):
            # Internal error, this should not happen
            raise Exception('Tried to save user document with no salt.')

        if not doc['fname']:
            raise ValidationException('First name must not be empty.', 'firstName')

        if not doc['lname']:
            raise ValidationException('Last name must not be empty.', 'lastName')

        if '@' in doc['login']:
            # Hard-code this one so we can always easily distinguish email from login
            raise ValidationException('Login may not contain "@".', 'login')

        if not re.match(cherrypy.config['users']['login_regex'], doc['login']):
            raise ValidationException(cherrypy.config['users']['login_description'], 'login')

        if not re.match(cherrypy.config['users']['email_regex'], doc['email']):
            raise ValidationException('Invalid email address.', 'email')

        # Ensure unique logins
        q = {'login': doc['login']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.find(q, limit=1)
        if existing.count(True) > 0:
            raise ValidationException('That login is already registered.', 'login')

        # Ensure unique emails
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.find(q, limit=1)
        if existing.count(True) > 0:
            raise ValidationException('That email is already registered.', 'email')

        return doc

    def createUser(self, login, password, firstName, lastName, email,
                   admin=False, public=True):
        """
        Create a new user with the given information. The user will be created
        with the default "Public" and "Private" folders. Validation must be done
        in advance by the caller.
        :param admin: Whether user is global administrator.
        :type admin: bool
        :param tokenLifespan: Number of days the long-term token should last.
        :type tokenLifespan: int
        :param public: Whether user is publicly visible.
        :type public: bool
        :returns: The user document that was created.
        """
        (salt, hashAlg) = self.passwordModel.encryptAndStore(password)

        user = self.save({
            'login': login,
            'email': email,
            'firstName': firstName,
            'lastName': lastName,
            'salt': salt,
            'created': datetime.datetime.now(),
            'hashAlg': hashAlg,
            'emailVerified': False,
            'admin': admin,
            'size': 0
            })

        user = self.setPublic(user, public=public, save=False)
        # Must have already saved the user prior to calling this since we are
        # granting the user access on himself.
        user = self.setUserAccess(user, user, level=AccessType.ADMIN, save=True)

        # Create some default folders for the user and give the user admin access to them
        publicFolder = self.folderModel.createFolder(user, 'Public', parentType='user',
                                                     public=True, creator=user)
        privateFolder = self.folderModel.createFolder(user, 'Private', parentType='user',
                                                      public=False, creator=user)
        self.folderModel.setUserAccess(publicFolder, user, AccessType.ADMIN)
        self.folderModel.setUserAccess(privateFolder, user, AccessType.ADMIN)

        return user
