# -*- coding: utf-8 -*-
import datetime
import os
import re
from passlib.context import CryptContext
from passlib.totp import TOTP, TokenError

from .model_base import AccessControlledModel
from .setting import Setting
from girder import events
from girder.constants import AccessType, CoreEventHandler, TokenScope
from girder.exceptions import AccessException, ValidationException
from girder.settings import SettingKey
from girder.utility import config, mail_utils
from girder.utility._cache import rateLimitBuffer


class User(AccessControlledModel):
    """
    This model represents the users of the system.
    """

    def initialize(self):
        self.name = 'user'
        self.ensureIndices(['login', 'email', 'groupInvites.groupId', 'size',
                            'created'])
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

        # To ensure compatibility with authenticator apps, other defaults shouldn't be changed
        self._TotpFactory = TOTP.using(
            # An application secret could be set here, if it existed
            wallet=None
        )

        self._cryptContext = CryptContext(
            schemes=['bcrypt']
        )

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

        if 'salt' not in doc:
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

        if 'hashAlg' in doc:
            # This is a legacy field; hash algorithms are now inline with the password hash
            del doc['hashAlg']

        self._validateLogin(doc['login'])

        if not mail_utils.validateEmailAddress(doc['email']):
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

    def _validateLogin(self, login):
        if '@' in login:
            # Hard-code this constraint so we can always easily distinguish
            # an email address from a login
            raise ValidationException('Login may not contain "@".', 'login')

        if not re.match(r'^[a-z][\da-z\-\.]{3,}$', login):
            raise ValidationException(
                'Login must be at least 4 characters, start with a letter, and may only contain '
                'letters, numbers, dashes, and dots.', 'login')

    def filter(self, doc, user, additionalKeys=None):
        filteredDoc = super(User, self).filter(doc, user, additionalKeys)

        level = self.getAccessLevel(doc, user)
        if level >= AccessType.ADMIN:
            filteredDoc['otp'] = doc.get('otp', {}).get('enabled', False)

        return filteredDoc

    def authenticate(self, login, password, otpToken=None):
        """
        Validate a user login via username and password. If authentication fails,
        a ``AccessException`` is raised.

        :param login: The user's login or email.
        :type login: str
        :param password: The user's password.
        :type password: str
        :param otpToken: A one-time password for the user. If "True", then the one-time password
                         (if required) is assumed to be concatenated to the password.
        :type otpToken: str or bool or None
        :returns: The corresponding user if the login was successful.
        :rtype: dict
        """
        event = events.trigger('model.user.authenticate', {
            'login': login,
            'password': password
        })

        if event.defaultPrevented and len(event.responses):
            return event.responses[-1]

        login = login.lower().strip()
        loginField = 'email' if '@' in login else 'login'

        user = self.findOne({loginField: login})
        if user is None:
            raise AccessException('Login failed.')

        # Handle users with no password
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

        # Handle OTP token concatenation
        if otpToken is True and self.hasOtpEnabled(user):
            # Assume the last (typically 6) characters are the OTP, so split at that point
            otpTokenLength = self._TotpFactory.digits
            otpToken = password[-otpTokenLength:]
            password = password[:-otpTokenLength]

        # Verify password
        if not self._cryptContext.verify(password, user['salt']):
            raise AccessException('Login failed.')

        # Verify OTP
        if self.hasOtpEnabled(user):
            if otpToken is None:
                raise AccessException(
                    'User authentication must include a one-time password '
                    '(typically in the "Girder-OTP" header).')
            self.verifyOtp(user, otpToken)
        elif isinstance(otpToken, str):
            raise AccessException('The user has not enabled one-time passwords.')

        # This has the same behavior as User.canLogin, but returns more
        # detailed error messages
        if user.get('status', 'enabled') == 'disabled':
            raise AccessException('Account is disabled.', extra='disabled')

        if self.emailVerificationRequired(user):
            raise AccessException(
                'Email verification required.', extra='emailVerification')

        if self.adminApprovalRequired(user):
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
        from .folder import Folder
        from .group import Group
        from .token import Token

        # Delete all authentication tokens owned by this user
        Token().removeWithQuery({'userId': user['_id']})

        # Delete all pending group invites for this user
        Group().update(
            {'requests': user['_id']},
            {'$pull': {'requests': user['_id']}}
        )

        # Delete all of the folders under this user
        folderModel = Folder()
        folders = folderModel.find({
            'parentId': user['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            folderModel.remove(folder, progress=progress, **kwargs)

        # Finally, delete the user document itself
        AccessControlledModel.remove(self, user)
        if progress:
            progress.update(increment=1, message='Deleted user ' + user['login'])

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

    def hasPassword(self, user):
        """
        Returns whether or not the given user has a password stored in the
        database. If not, it is expected that the user will be authenticated by
        an external service.

        :param user: The user to test.
        :type user: dict
        :returns: bool
        """
        return user['salt'] is not None

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
            cur_config = config.getConfig()

            # Normally this would go in validate() but password is a special case.
            if not re.match(cur_config['users']['password_regex'], password):
                raise ValidationException(cur_config['users']['password_description'], 'password')

            user['salt'] = self._cryptContext.hash(password)

        if save:
            self.save(user)

    def initializeOtp(self, user):
        """
        Initialize the use of one-time passwords with this user.

        This does not save the modified user model.

        :param user: The user to modify.
        :return: The new OTP keys, each in KeyUriFormat.
        :rtype: dict
        """
        totp = self._TotpFactory.new()

        user['otp'] = {
            'enabled': False,
            'totp': totp.to_dict()
        }

        # Use the brand name as the OTP issuer if it's non-default (since that's prettier and more
        # meaningful for users), but fallback to the site hostname if the brand name isn't set
        # (to disambiguate otherwise identical "Girder" issuers)
        # Prevent circular import
        from girder.api.rest import getUrlParts
        brandName = Setting().get(SettingKey.BRAND_NAME)
        defaultBrandName = Setting().getDefault(SettingKey.BRAND_NAME)
        # OTP URIs ( https://github.com/google/google-authenticator/wiki/Key-Uri-Format ) do not
        # allow colons, so use only the hostname component
        serverHostname = getUrlParts().netloc.partition(':')[0]
        # Normally, the issuer would be set when "self._TotpFactory" is instantiated, but that
        # happens during model initialization, when there's no current request, so the server
        # hostname is not known then
        otpIssuer = brandName if brandName != defaultBrandName else serverHostname

        return {
            'totpUri': totp.to_uri(label=user['login'], issuer=otpIssuer)
        }

    def hasOtpEnabled(self, user):
        return 'otp' in user and user['otp']['enabled']

    def verifyOtp(self, user, otpToken):
        lastCounterKey = 'girder.models.user.%s.otp.totp.counter' % user['_id']

        # The last successfully-authenticated key (which is blacklisted from reuse)
        lastCounter = rateLimitBuffer.get(lastCounterKey) or None

        try:
            totpMatch = self._TotpFactory.verify(
                otpToken, user['otp']['totp'], last_counter=lastCounter)
        except TokenError as e:
            raise AccessException('One-time password validation failed: %s' % e)

        # The totpMatch.cache_seconds tells us prospectively how long the counter needs to be cached
        # for, but dogpile.cache expiration times work retrospectively (on "get"), so there's no
        # point to using it (over-caching just wastes cache resources, but does not impact
        # "totp.verify" security)
        rateLimitBuffer.set(lastCounterKey, totpMatch.counter)

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
        from .setting import Setting
        requireApproval = Setting().get(SettingKey.REGISTRATION_POLICY) == 'approve'
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

        verifyEmail = Setting().get(SettingKey.EMAIL_VERIFICATION) != 'disabled'
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
        from .setting import Setting
        return (not user['emailVerified']) and \
            Setting().get(SettingKey.EMAIL_VERIFICATION) == 'required'

    def adminApprovalRequired(self, user):
        """
        Returns True if the registration policy requires admin approval and
        this user is pending approval.
        """
        from .setting import Setting
        return user.get('status', 'enabled') == 'pending' and \
            Setting().get(SettingKey.REGISTRATION_POLICY) == 'approve'

    def _sendApprovalEmail(self, user):
        url = '%s#user/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']))
        text = mail_utils.renderTemplate('accountApproval.mako', {
            'user': user,
            'url': url
        })
        mail_utils.sendMailToAdmins(
            'Girder: Account pending approval',
            text)

    def _sendApprovedEmail(self, user):
        text = mail_utils.renderTemplate('accountApproved.mako', {
            'user': user,
            'url': mail_utils.getEmailUrlPrefix()
        })
        mail_utils.sendMail(
            'Girder: Account approved',
            text,
            [user.get('email')])

    def _sendVerificationEmail(self, user):
        from .token import Token

        token = Token().createToken(
            user, days=1, scope=TokenScope.EMAIL_VERIFICATION)
        url = '%s#useraccount/%s/verification/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))
        text = mail_utils.renderTemplate('emailVerification.mako', {
            'url': url
        })
        mail_utils.sendMail(
            'Girder: Email verification',
            text,
            [user.get('email')])

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
        from .folder import Folder
        from .setting import Setting

        if Setting().get(SettingKey.USER_DEFAULT_FOLDERS) == 'public_private':
            user = event.info

            publicFolder = Folder().createFolder(
                user, 'Public', parentType='user', public=True, creator=user)
            privateFolder = Folder().createFolder(
                user, 'Private', parentType='user', public=False, creator=user)
            # Give the user admin access to their own folders
            Folder().setUserAccess(publicFolder, user, AccessType.ADMIN, save=True)
            Folder().setUserAccess(privateFolder, user, AccessType.ADMIN, save=True)

    def fileList(self, doc, user=None, path='', includeMetadata=False, subpath=True, data=True):
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
        from .folder import Folder

        if subpath:
            path = os.path.join(path, doc['login'])
        folderModel = Folder()
        # Eagerly evaluate this list, as the MongoDB cursor can time out on long requests
        childFolders = list(folderModel.childFolders(
            parentType='user', parent=doc, user=user,
            fields=['name'] + (['meta'] if includeMetadata else [])
        ))
        for folder in childFolders:
            for (filepath, file) in folderModel.fileList(
                    folder, user, path, includeMetadata, subpath=True, data=data):
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
        from .folder import Folder

        count = 1
        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        }, fields='access', user=user, level=level)

        count += sum(folderModel.subtreeCount(
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
        from .folder import Folder

        fields = () if level is None else ('access', 'public')

        folderModel = Folder()
        folders = folderModel.findWithPermissions({
            'parentId': user['_id'],
            'parentCollection': 'user'
        }, fields=fields, user=filterUser, level=level)

        return folders.count()

    def updateSize(self, doc):
        """
        Recursively recomputes the size of this user and its underlying
        folders and fixes the sizes as needed.

        :param doc: The user.
        :type doc: dict
        """
        from .folder import Folder

        size = 0
        fixes = 0
        folderModel = Folder()
        folders = folderModel.find({
            'parentId': doc['_id'],
            'parentCollection': 'user'
        })
        for folder in folders:
            # fix folder size if needed
            _, f = folderModel.updateSize(folder)
            fixes += f
            # get total recursive folder size
            folder = folderModel.load(folder['_id'], force=True)
            size += folderModel.getSizeRecursive(folder)
        # fix value if incorrect
        if size != doc.get('size'):
            self.update({'_id': doc['_id']}, update={'$set': {'size': size}})
            fixes += 1
        return size, fixes
