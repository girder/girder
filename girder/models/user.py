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
import os
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

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'login', 'public', 'firstName', 'lastName', 'admin',
            'created'))
        self.exposeFields(level=AccessType.ADMIN, fields=(
            'size', 'email', 'groups', 'groupInvites'))

    def filter(self, user, currentUser):
        """Preserved override for kwarg backwards compatibility."""
        return AccessControlledModel.filter(self, doc=user, user=currentUser)

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        doc['login'] = doc.get('login', '').lower().strip()
        doc['email'] = doc.get('email', '').lower().strip()
        doc['firstName'] = doc.get('firstName', '').strip()
        doc['lastName'] = doc.get('lastName', '').strip()

        cur_config = config.getConfig()

        if 'salt' not in doc:  # pragma: no cover
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
        existing = self.findOne(q)
        if existing is not None:
            raise ValidationException('That login is already registered.',
                                      'login')

        # Ensure unique emails
        q = {'email': doc['email']}
        if '_id' in doc:
            q['_id'] = {'$ne': doc['_id']}
        existing = self.findOne(q)
        if existing is not None:
            raise ValidationException('That email is already registered.',
                                      'email')

        # If this is the first user being created, make it an admin
        existing = self.findOne({})
        if existing is None:
            doc['admin'] = True

        return doc

    def remove(self, user, progress=None, **kwargs):
        """
        Delete a user, and all references to it in the database.

        :param user: The user document to delete.
        :type user: dict
        :param progress: A progress context to record progress on.
        :type progress: girder.utility.progress.ProgressContext or None.
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
        })
        for folder in folders:
            self.model('folder').remove(folder, progress=progress, **kwargs)

        # Finally, delete the user document itself
        AccessControlledModel.remove(self, user)
        if progress:
            progress.update(increment=1, message='Deleted user ' +
                            user['login'])

    def getAdmins(self):
        """
        Helper to return a cursor of all site-admin users. The number of site
        admins is assumed to be small enough that we will not need to page the
        results for now.
        """
        return self.find({'admin': True})

    def search(self, text=None, user=None, limit=0, offset=0, sort=None):
        """
        List all users. Since users are access-controlled, this will filter
        them by access policy.

        :param text: Pass this to perform a full-text search for users.
        :param user: The user running the query. Only returns users that this
                     user can see.
        :param limit: Result limit.
        :param offset: Result offset.
        :param sort: The sort structure to pass to pymongo.
        :returns: Iterable of users.
        """
        # Perform the find; we'll do access-based filtering of the result set
        # afterward.
        if text is not None:
            cursor = self.textSearch(text, sort=sort)
        else:
            cursor = self.find({}, sort=sort)

        return self.filterResultsByPermission(
            cursor=cursor, user=user, level=AccessType.READ, limit=limit,
            offset=offset)

    def setPassword(self, user, password, save=True):
        """
        Change a user's password.

        :param user: The user whose password to change.
        :param password: The new password. If set to None, no password will
                         be stored for this user. This should be done in cases
                         where an external system is responsible for
                         authenticating the user.
        """
        if password is None:
            user['salt'] = None
        else:
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
            'created': datetime.datetime.utcnow(),
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

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True):
        """
        Generate a list of files within this user's folders.

        :param doc: the user to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the json string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the user's name to the path.
        """
        if subpath:
            path = os.path.join(path, doc['login'])
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            for (filepath, file) in self.model('folder').fileList(
                    folder, user, path, includeMetadata, subpath=True):
                yield (filepath, file)

    def subtreeCount(self, doc):
        """
        Return the size of the user's folders.  The user is counted as well.

        :param doc: The user.
        """
        count = 1
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        })
        count += sum(self.model('folder').subtreeCount(folder)
                     for folder in folders)
        return count
