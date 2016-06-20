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
from girder import events
from girder.constants import AccessType, CoreEventHandler, SettingKey
from girder.utility import config


class User(AccessControlledModel):
    """
    This model represents the users of the system.
    """

    def initialize(self):
        self.name = 'user'
        self.ensureIndices(['login', 'email', 'groupInvites.groupId'])
        self.prefixSearchFields = (
            'login', ('firstName', 'i'), ('lastName', 'i'))

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

        events.bind('model.user.save.created',
                    CoreEventHandler.USER_SELF_ACCESS, self._grantSelfAccess)
        events.bind('model.user.save.created',
                    CoreEventHandler.USER_DEFAULT_FOLDERS,
                    self._addDefaultFolders)

    def filter(self, *args, **kwargs):
        """
        Preserved override for kwarg backwards compatibility. Prior to the
        refactor for centralizing model filtering, this method's first formal
        parameter was called "folder", whereas the centralized version's first
        parameter is called "doc". This override simply detects someone using
        the old kwarg and converts it to the new form.
        """
        if 'currentUser' in kwargs and 'user' in kwargs:
            args = [kwargs.pop('user')] + list(args)
            kwargs['user'] = kwargs.pop('currentUser')
        return super(User, self).filter(*args, **kwargs)

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
        # Delete all authentication tokens owned by this user
        self.model('token').removeWithQuery({'userId': user['_id']})

        # Delete all pending group invites for this user
        self.model('group').update(
            {'requests': user['_id']},
            {'$pull': {'requests': user['_id']}}
        )

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
            'groups': [],
            'groupInvites': []
        }

        self.setPassword(user, password, save=False)
        self.setPublic(user, public, save=False)

        verifyEmail = self.model('setting').get(
            SettingKey.EMAIL_VERIFICATION) == 'required'

        if verifyEmail:
            pass # send email

        return self.save(user)

    def _grantSelfAccess(self, event):
        """
        This callback grants a user admin access to itself.

        This generally should not be called or overridden directly, but it may
        be unregistered from the `model.user.save.created` event.
        """
        user = event.info

        self.setUserAccess(user, user, level=AccessType.ADMIN, save=True)

    def _addDefaultFolders(self, event):
        """
        This callback creates "Public" and "Private" folders on a user, after
        it is first created.

        This generally should not be called or overridden directly, but it may
        be unregistered from the `model.user.save.created` event.
        """
        if self.model('setting').get(
                SettingKey.USER_DEFAULT_FOLDERS, 'public_private') \
                == 'public_private':
            user = event.info

            publicFolder = self.model('folder').createFolder(
                user, 'Public', parentType='user', public=True, creator=user)
            privateFolder = self.model('folder').createFolder(
                user, 'Private', parentType='user', public=False, creator=user)
            # Give the user admin access to their own folders
            self.model('folder').setUserAccess(
                publicFolder, user, AccessType.ADMIN, save=True)
            self.model('folder').setUserAccess(
                privateFolder, user, AccessType.ADMIN, save=True)

    def fileList(self, doc, user=None, path='', includeMetadata=False,
                 subpath=True):
        """
        Generate a list of files within this user's folders.

        :param doc: the user to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the user's name to the path.
        """
        if subpath:
            path = os.path.join(path, doc['login'])
        for folder in self.model('folder').childFolders(parentType='user',
                                                        parent=doc, user=user):
            for (filepath, file) in self.model('folder').fileList(
                    folder, user, path, includeMetadata, subpath=True):
                yield (filepath, file)

    def subtreeCount(self, doc, includeItems=True, user=None, level=None):
        """
        Return the size of the user's folders.  The user is counted as well.

        :param doc: The user.
        :param includeItems: Whether to include items in the subtree count, or
            just folders.
        :type includeItems: bool
        :param user: If filtering by permission, the user to filter against.
        :param level: If filtering by permission, the required permission level.
        :type level: AccessLevel
        """
        count = 1
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        }, fields=('access',))

        if level is not None:
            folders = self.filterResultsByPermission(
                cursor=folders, user=user, level=level)

        count += sum(self.model('folder').subtreeCount(
            folder, includeItems=includeItems, user=user, level=level)
            for folder in folders)
        return count

    def countFolders(self, user, filterUser=None, level=None):
        """
        Returns the number of top level folders under this user. Access
        checking is optional; to circumvent access checks, pass ``level=None``.

        :param user: The user whose top level folders to count.
        :type collection: dict
        :param filterUser: If performing access checks, the user to check
            against.
        :type filterUser: dict or None
        :param level: The required access level, or None to return the raw
            top-level folder count.
        """
        fields = () if level is None else ('access', 'public')

        folderModel = self.model('folder')
        folders = folderModel.find({
            'parentId': user['_id'],
            'parentCollection': 'user'
        }, fields=fields)

        if level is None:
            return folders.count()
        else:
            return sum(1 for _ in folderModel.filterResultsByPermission(
                cursor=folders, user=filterUser, level=level))

    def updateSize(self, doc, user):
        """
        Recursively recomputes the size of this user and its underlying
        folders and fixes the sizes as needed.

        :param doc: The user.
        :type doc: dict
        :param user: The admin user for permissions.
        :type user: dict
        """
        size = 0
        fixes = 0
        folders = self.model('folder').childFolders(doc, 'user', user)
        for folder in folders:
            # fix folder size if needed
            _, f = self.model('folder').updateSize(folder, user)
            fixes += f
            # get total recursive folder size
            folder = self.model('folder').load(folder['_id'], user=user)
            size += self.model('folder').getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
