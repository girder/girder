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

import datetime
import re

from .model_base import AccessControlledModel, ValidationException
from girder.constants import AccessType
from girder.utility import config


class User(AccessControlledModel):
    """
    This model represents the users of the system.
    """

    def initialize(self):
        self.name = 'user'
        self.ensureIndices(['login', 'email', 'groupInvites.groupId'])
        self.ensureTextIndex({
            'login': 1,
            'firstName': 1,
            'lastName': 1
        }, language='none')

    def filter(self, user, currentUser):
        if user is None:
            return None

        keys = ['_id', 'login', 'public', 'firstName', 'lastName', 'admin',
                'created']

        if self.hasAccess(user, currentUser, AccessType.ADMIN):
            keys.extend(['size', 'email', 'groups', 'groupInvites'])

        filtered = self.filterDocument(user, allow=keys)

        filtered['_accessLevel'] = self.getAccessLevel(user, currentUser)

        return filtered

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        doc['login'] = doc.get('login', '').lower().strip()
        doc['email'] = doc.get('email', '').lower().strip()
        doc['firstName'] = doc.get('firstName', '').strip()
        doc['lastName'] = doc.get('lastName', '').strip()

        cur_config = config.getConfig()

        if not doc.get('salt', ''):  # pragma: no cover
            # Internal error, this should not happen
            raise Exception('Tried to save user document with no salt.')

        if not doc['firstName']:
            raise ValidationException('First name must not be empty.',
                                      'firstName')

        if not doc['lastName']:
            raise ValidationException('Last name must not be empty.',
                                      'lastName')

        if '@' in doc['login']:
            # Hard-code this constraint so we can always easily distinguish
            # an email address from a login
            raise ValidationException('Login may not contain "@".', 'login')

        if not re.match(cur_config['users']['login_regex'], doc['login']):
            raise ValidationException(
                cur_config['users']['login_description'], 'login')

        if not re.match(cur_config['users']['email_regex'], doc['email']):
            raise ValidationException('Invalid email address.', 'email')

        # Ensure unique logins
        q = {'login': doc['login']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.find(q, limit=1)
        if existing.count(True) > 0:
            raise ValidationException('That login is already registered.',
                                      'login')

        # Ensure unique emails
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.find(q, limit=1)
        if existing.count(True) > 0:
            raise ValidationException('That email is already registered.',
                                      'email')

        # If this is the first user being created, make it an admin
        existing = self.find({}, limit=1)
        if existing.count(True) == 0:
            doc['admin'] = True

        return doc

    def remove(self, user):
        """
        Delete a user, and all references to it in the database.

        :param user: The user document to delete.
        :type user: dict
        """
        # Remove creator references for this user.
        creatorQuery = {
            'creatorId': user['_id']
        }
        creatorUpdate = {
            '$set': {'creatorId': None}
        }
        self.model('collection').update(creatorQuery, creatorUpdate)
        self.model('folder').update(creatorQuery, creatorUpdate)
        self.model('item').update(creatorQuery, creatorUpdate)

        # Remove references to this user from access-controlled resources.
        acQuery = {
            'access.users.id': user['_id']
        }
        acUpdate = {
            '$pull': {
                'access.users': {'id': user['_id']}
            }
        }
        self.update(acQuery, acUpdate)
        self.model('collection').update(acQuery, acUpdate)
        self.model('folder').update(acQuery, acUpdate)
        self.model('group').update(acQuery, acUpdate)

        # Delete all authentication tokens owned by this user
        self.model('token').removeWithQuery({'userId': user['_id']})

        # Delete all of the folders under this user
        folders = self.model('folder').find({
            'parentId': user['_id'],
            'parentCollection': 'user'
        }, limit=0)
        for folder in folders:
            self.model('folder').remove(folder)

        # Finally, delete the user document itself
        AccessControlledModel.remove(self, user)

    def search(self, text=None, user=None, limit=50, offset=0, sort=None):
        """
        List all users. Since users are access-controlled, this will filter
        them by access policy.

        :param text: Pass this to perform a full-text search for users.
        :param user: The user running the query. Only returns users that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :returns: List of users.
        """
        # TODO support full-text search

        # Perform the find; we'll do access-based filtering of the result set
        # afterward.
        cursor = self.find({}, limit=0, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=user,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def setPassword(self, user, password, save=True):
        """
        Change a user's password.

        :param user: The user whose password to change.
        :param password: The new password.
        """
        salt, alg = self.model('password').encryptAndStore(password)
        user['salt'] = salt
        user['hashAlg'] = alg

        if save:
            self.save(user)

    def createUser(self, login, password, firstName, lastName, email,
                   admin=False, public=True):
        """
        Create a new user with the given information. The user will be created
        with the default "Public" and "Private" folders.

        :param admin: Whether user is global administrator.
        :type admin: bool
        :param public: Whether user is publicly visible.
        :type public: bool
        :returns: The user document that was created.
        """
        user = {
            'login': login,
            'email': email,
            'firstName': firstName,
            'lastName': lastName,
            'created': datetime.datetime.now(),
            'emailVerified': False,
            'admin': admin,
            'size': 0,
            'groupInvites': []
        }

        self.setPassword(user, password)

        self.setPublic(user, public=public)
        # Must have already saved the user prior to calling this since we are
        # granting the user access on himself.
        self.setUserAccess(user, user, level=AccessType.ADMIN, save=True)

        # Create some default folders for the user and give the user admin
        # access to them
        publicFolder = self.model('folder').createFolder(
            user, 'Public', parentType='user', public=True, creator=user)
        privateFolder = self.model('folder').createFolder(
            user, 'Private', parentType='user', public=False, creator=user)
        self.model('folder').setUserAccess(
            publicFolder, user, AccessType.ADMIN, save=True)
        self.model('folder').setUserAccess(
            privateFolder, user, AccessType.ADMIN, save=True)

        return user
