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

from .model_base import AccessControlledModel, AccessException, ValidationException
from girder import events
from girder.constants import AccessType, CoreEventHandler, SettingKey, TokenScope
from girder.utility import config, mail_utils


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
            'size', 'email', 'groups', 'groupInvites', 'status',
            'emailVerified'))

        events.bind('model.user.save.created',
                    CoreEventHandler.USER_SELF_ACCESS, self._grantSelfAccess)
        events.bind('model.user.save.created',
                    CoreEventHandler.USER_DEFAULT_FOLDERS,
                    self._addDefaultFolders)

    def validate(self, doc):
        """
        Validate the user every time it is stored in the database.
        """
        doc['login'] = doc.get('login', '').lower().strip()
        doc['email'] = doc.get('email', '').lower().strip()
        doc['firstName'] = doc.get('firstName', '').strip()
        doc['lastName'] = doc.get('lastName', '').strip()
        doc['status'] = doc.get('status', 'enabled')

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

        if doc['status'] not in ('pending', 'enabled', 'disabled'):
            raise ValidationException(
                'Status must be pending, enabled, or disabled.', 'status')

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
            # Ensure settings don't stop this user from logging in
            doc['emailVerified'] = True
            doc['status'] = 'enabled'

        return doc

    def authenticate(self, login, password):
        """
        Validate a user login via username and password. If authentication fails,
        a ``AccessException`` is raised.

        :param login: The user's login or email.
        :type login: str
        :param password: The user's password.
        :type password: str
        :returns: The corresponding user if the login was successful.
        :rtype: dict
        """
        login = login.lower().strip()
        loginField = 'email' if '@' in login else 'login'

        user = self.model('user').findOne({loginField: login})
        if user is None:
            raise AccessException('Login failed.')

        if not self.model('password').authenticate(user, password):
            raise AccessException('Login failed.')

        # This has the same behavior as User.canLogin, but returns more
        # detailed error messages
        if user.get('status', 'enabled') == 'disabled':
            raise AccessException('Account is disabled.', extra='disabled')

        if self.model('user').emailVerificationRequired(user):
            raise AccessException(
                'Email verification required.', extra='emailVerification')

        if self.model('user').adminApprovalRequired(user):
            raise AccessException('Account approval required.', extra='accountApproval')

        return user

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
        requireApproval = self.model('setting').get(
            SettingKey.REGISTRATION_POLICY) == 'approve'
        if admin:
            requireApproval = False

        user = {
            'login': login,
            'email': email,
            'firstName': firstName,
            'lastName': lastName,
            'created': datetime.datetime.utcnow(),
            'emailVerified': False,
            'status': 'pending' if requireApproval else 'enabled',
            'admin': admin,
            'size': 0,
            'groups': [],
            'groupInvites': []
        }

        self.setPassword(user, password, save=False)
        self.setPublic(user, public, save=False)

        user = self.save(user)

        verifyEmail = self.model('setting').get(
            SettingKey.EMAIL_VERIFICATION) != 'disabled'
        if verifyEmail:
            self._sendVerificationEmail(user)

        if requireApproval:
            self._sendApprovalEmail(user)

        return user

    def canLogin(self, user):
        """
        Returns True if the user is allowed to login, e.g. email verification
        is not needed and admin approval is not needed.
        """
        if user.get('status', 'enabled') == 'disabled':
            return False
        if self.emailVerificationRequired(user):
            return False
        if self.adminApprovalRequired(user):
            return False
        return True

    def emailVerificationRequired(self, user):
        """
        Returns True if email verification is required and this user has not
        yet verified their email address.
        """
        return (not user['emailVerified']) and self.model('setting').get(
            SettingKey.EMAIL_VERIFICATION) == 'required'

    def adminApprovalRequired(self, user):
        """
        Returns True if the registration policy requires admin approval and
        this user is pending approval.
        """
        return user.get('status', 'enabled') == 'pending' and \
            self.model('setting').get(
                SettingKey.REGISTRATION_POLICY) == 'approve'

    def _sendApprovalEmail(self, user):
        url = '%s#user/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']))
        text = mail_utils.renderTemplate('accountApproval.mako', {
            'user': user,
            'url': url
        })
        mail_utils.sendEmail(
            toAdmins=True,
            subject='Girder: Account pending approval',
            text=text)

    def _sendApprovedEmail(self, user):
        text = mail_utils.renderTemplate('accountApproved.mako', {
            'user': user,
            'url': mail_utils.getEmailUrlPrefix()
        })
        mail_utils.sendEmail(
            to=user.get('email'),
            subject='Girder: Account approved',
            text=text)

    def _sendVerificationEmail(self, user):
        token = self.model('token').createToken(
            user, days=1, scope=TokenScope.EMAIL_VERIFICATION)
        url = '%s#useraccount/%s/verification/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))
        text = mail_utils.renderTemplate('emailVerification.mako', {
            'url': url
        })
        mail_utils.sendEmail(
            to=user.get('email'),
            subject='Girder: Email verification',
            text=text)

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
                 subpath=True, data=True):
        """
        This function generates a list of 2-tuples whose first element is the
        relative path to the file from the user's folders root and whose second
        element depends on the value of the `data` flag. If `data=True`, the
        second element will be a generator that will generate the bytes of the
        file data as stored in the assetstore. If `data=False`, the second
        element is the file document itself.

        :param doc: the user to list.
        :param user: a user used to validate data that is returned.
        :param path: a path prefix to add to the results.
        :param includeMetadata: if True and there is any metadata, include a
                                result which is the JSON string of the
                                metadata.  This is given a name of
                                metadata[-(number).json that is distinct from
                                any file within the item.
        :param subpath: if True, add the user's name to the path.
        :param data: If True return raw content of each file as stored in the
            assetstore, otherwise return file document.
        :type data: bool
        """
        if subpath:
            path = os.path.join(path, doc['login'])
        for folder in self.model('folder').childFolders(parentType='user',
                                                        parent=doc, user=user):
            for (filepath, file) in self.model('folder').fileList(
                    folder, user, path, includeMetadata, subpath=True,
                    data=data):
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

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this user and its underlying
        folders and fixes the sizes as needed.

        :param doc: The user.
        :type doc: dict
        """
        size = 0
        fixes = 0
        folders = self.model('folder').find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            # fix folder size if needed
            _, f = self.model('folder').updateSize(folder)
            fixes += f
            # get total recursive folder size
            folder = self.model('folder').load(folder['_id'], force=True)
            size += self.model('folder').getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
