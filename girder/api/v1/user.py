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

import base64
import cherrypy
import datetime

from ..describe import Description, autoDescribeRoute
from girder.api import access
from girder.api.rest import Resource, filtermodel, setCurrentUser
from girder.constants import AccessType, SettingKey, TokenScope
from girder.exceptions import RestException, AccessException
from girder.models.password import Password
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User as UserModel
from girder.utility import mail_utils


class User(Resource):
    """API Endpoint for users in the system."""

    def __init__(self):
        super(User, self).__init__()
        self.resourceName = 'user'
        self._model = UserModel()

        self.route('DELETE', ('authentication',), self.logout)
        self.route('DELETE', (':id',), self.deleteUser)
        self.route('GET', (), self.find)
        self.route('GET', ('me',), self.getMe)
        self.route('GET', ('authentication',), self.login)
        self.route('GET', (':id',), self.getUser)
        self.route('GET', (':id', 'details'), self.getUserDetails)
        self.route('GET', ('details',), self.getUsersDetails)
        self.route('POST', (), self.createUser)
        self.route('PUT', (':id',), self.updateUser)
        self.route('PUT', ('password',), self.changePassword)
        self.route('PUT', (':id', 'password'), self.changeUserPassword)
        self.route('GET', ('password', 'temporary', ':id'),
                   self.checkTemporaryPassword)
        self.route('PUT', ('password', 'temporary'),
                   self.generateTemporaryPassword)
        self.route('POST', (':id', 'otp'), self.initializeOtp)
        self.route('PUT', (':id', 'otp'), self.finalizeOtp)
        self.route('DELETE', (':id', 'otp'), self.removeOtp)
        self.route('PUT', (':id', 'verification'), self.verifyEmail)
        self.route('POST', ('verification',), self.sendVerificationEmail)

    @access.user
    @filtermodel(model=UserModel)
    @autoDescribeRoute(
        Description('List or search for users.')
        .responseClass('User', array=True)
        .param('text', "Pass this to perform a full text search for items.", required=False)
        .pagingParams(defaultSort='lastName')
    )
    def find(self, text, limit, offset, sort):
        return list(self._model.search(
            text=text, user=self.getCurrentUser(), offset=offset, limit=limit, sort=sort))

    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model=UserModel)
    @autoDescribeRoute(
        Description('Get a user by ID.')
        .responseClass('User')
        .modelParam('id', model=UserModel, level=AccessType.READ)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to see this user.', 403)
    )
    def getUser(self, user):
        return user

    @access.public(scope=TokenScope.USER_INFO_READ)
    @filtermodel(model=UserModel)
    @autoDescribeRoute(
        Description('Retrieve the currently logged-in user information.')
        .responseClass('User')
    )
    def getMe(self):
        return self.getCurrentUser()

    @access.public
    @autoDescribeRoute(
        Description('Log in to the system.')
        .notes('Pass your username and password using HTTP Basic Auth. Sends'
               ' a cookie that should be passed back in future requests.')
        .param('Girder-OTP', 'A one-time password for this user', paramType='header',
               required=False)
        .errorResponse('Missing Authorization header.', 401)
        .errorResponse('Invalid login or password.', 403)
    )
    def login(self):
        if not Setting().get(SettingKey.ENABLE_PASSWORD_LOGIN):
            raise RestException('Password login is disabled on this instance.')

        user, token = self.getCurrentUser(returnToken=True)

        # Only create and send new cookie if user isn't already sending a valid one.
        if not user:
            authHeader = cherrypy.request.headers.get('Girder-Authorization')

            if not authHeader:
                authHeader = cherrypy.request.headers.get('Authorization')

            if not authHeader or not authHeader[0:6] == 'Basic ':
                raise RestException('Use HTTP Basic Authentication', 401)

            try:
                credentials = base64.b64decode(authHeader[6:]).decode('utf8')
                if ':' not in credentials:
                    raise TypeError
            except Exception:
                raise RestException('Invalid HTTP Authorization header', 401)

            login, password = credentials.split(':', 1)
            otpToken = cherrypy.request.headers.get('Girder-OTP')
            user = self._model.authenticate(login, password, otpToken)

            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)

        return {
            'user': self._model.filter(user, user),
            'authToken': {
                'token': token['_id'],
                'expires': token['expires'],
                'scope': token['scope']
            },
            'message': 'Login succeeded.'
        }

    @access.public
    @autoDescribeRoute(
        Description('Log out of the system.')
        .responseClass('Token')
        .notes('Attempts to delete your authentication cookie.')
    )
    def logout(self):
        token = self.getCurrentToken()
        if token:
            Token().remove(token)
        self.deleteAuthTokenCookie()
        return {'message': 'Logged out.'}

    @access.public
    @filtermodel(model=UserModel, addFields={'authToken'})
    @autoDescribeRoute(
        Description('Create a new user.')
        .responseClass('User')
        .param('login', "The user's requested login.")
        .param('email', "The user's email address.")
        .param('firstName', "The user's first name.")
        .param('lastName', "The user's last name.")
        .param('password', "The user's requested password")
        .param('admin', 'Whether this user should be a site administrator.',
               required=False, dataType='boolean', default=False)
        .errorResponse('A parameter was invalid, or the specified login or'
                       ' email already exists in the system.')
    )
    def createUser(self, login, email, firstName, lastName, password, admin):
        currentUser = self.getCurrentUser()

        regPolicy = Setting().get(SettingKey.REGISTRATION_POLICY)

        if not currentUser or not currentUser['admin']:
            admin = False
            if regPolicy == 'closed':
                raise RestException(
                    'Registration on this instance is closed. Contact an '
                    'administrator to create an account for you.')

        user = self._model.createUser(
            login=login, password=password, email=email, firstName=firstName,
            lastName=lastName, admin=admin)

        if not currentUser and self._model.canLogin(user):
            setCurrentUser(user)
            token = self.sendAuthTokenCookie(user)
            user['authToken'] = {
                'token': token['_id'],
                'expires': token['expires']
            }
        return user

    @access.user
    @autoDescribeRoute(
        Description('Delete a user by ID.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('You do not have permission to delete this user.', 403)
    )
    def deleteUser(self, user):
        self._model.remove(user)
        return {'message': 'Deleted user %s.' % user['login']}

    @access.admin
    @autoDescribeRoute(
        Description('Get detailed information about all users.')
        .errorResponse('You are not a system administrator.', 403)
    )
    def getUsersDetails(self):
        nUsers = self._model.find().count()
        return {'nUsers': nUsers}

    @access.user
    @filtermodel(model=UserModel)
    @autoDescribeRoute(
        Description("Update a user's information.")
        .modelParam('id', model=UserModel, level=AccessType.WRITE)
        .param('firstName', 'First name of the user.')
        .param('lastName', 'Last name of the user.')
        .param('email', 'The email of the user.')
        .param('admin', 'Is the user a site admin (admin access required)',
               required=False, dataType='boolean')
        .param('status', 'The account status (admin access required)',
               required=False, enum=('pending', 'enabled', 'disabled'))
        .errorResponse()
        .errorResponse(('You do not have write access for this user.',
                        'Must be an admin to create an admin.'), 403)
    )
    def updateUser(self, user, firstName, lastName, email, admin, status):
        user['firstName'] = firstName
        user['lastName'] = lastName
        user['email'] = email

        # Only admins can change admin state
        if admin is not None:
            if self.getCurrentUser()['admin']:
                user['admin'] = admin
            elif user['admin'] is not admin:
                raise AccessException('Only admins may change admin status.')

        # Only admins can change status
        if status is not None and status != user.get('status', 'enabled'):
            if not self.getCurrentUser()['admin']:
                raise AccessException('Only admins may change status.')
            if user['status'] == 'pending' and status == 'enabled':
                # Send email on the 'pending' -> 'enabled' transition
                self._model._sendApprovedEmail(user)
            user['status'] = status

        return self._model.save(user)

    @access.admin
    @autoDescribeRoute(
        Description('Change a user\'s password.')
        .notes('Only administrators may use this endpoint.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .param('password', 'The user\'s new password.')
        .errorResponse('You are not an administrator.', 403)
        .errorResponse('The new password is invalid.')
    )
    def changeUserPassword(self, user, password):
        self._model.setPassword(user, password)
        return {'message': 'Password changed.'}

    @access.user
    @autoDescribeRoute(
        Description('Change your password.')
        .param('old', 'Your current password or a temporary access token.')
        .param('new', 'Your new password.')
        .errorResponse(('You are not logged in.',
                        'Your old password is incorrect.'), 401)
        .errorResponse('Your new password is invalid.')
    )
    def changePassword(self, old, new):
        user = self.getCurrentUser()
        token = None

        if not old:
            raise RestException('Old password must not be empty.')

        if not Password().hasPassword(user) or not Password().authenticate(user, old):
            # If not the user's actual password, check for temp access token
            token = Token().load(old, force=True, objectId=False, exc=False)
            if (not token or not token.get('userId') or
                    token['userId'] != user['_id'] or
                    not Token().hasScope(token, TokenScope.TEMPORARY_USER_AUTH)):
                raise AccessException('Old password is incorrect.')

        self._model.setPassword(user, new)

        if token:
            # Remove the temporary access token if one was used
            Token().remove(token)

        return {'message': 'Password changed.'}

    @access.public
    @autoDescribeRoute(
        Description('Create a temporary access token for a user.  The user\'s '
                    'password is not changed.')
        .param('email', 'Your email address.', strip=True)
        .errorResponse('That email does not exist in the system.')
    )
    def generateTemporaryPassword(self, email):
        user = self._model.findOne({'email': email.lower()})

        if not user:
            raise RestException('That email is not registered.')

        token = Token().createToken(user, days=1, scope=TokenScope.TEMPORARY_USER_AUTH)

        url = '%s#useraccount/%s/token/%s' % (
            mail_utils.getEmailUrlPrefix(), str(user['_id']), str(token['_id']))

        html = mail_utils.renderTemplate('temporaryAccess.mako', {
            'url': url,
            'token': str(token['_id'])
        })
        mail_utils.sendEmail(
            to=email, subject='%s: Temporary access' % Setting().get(SettingKey.BRAND_NAME),
            text=html
        )
        return {'message': 'Sent temporary access email.'}

    @access.public
    @autoDescribeRoute(
        Description('Check if a specified token is a temporary access token '
                    'for the specified user.  If the token is valid, returns '
                    'information on the token and user.')
        .modelParam('id', 'The user ID to check.', model=UserModel, force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token does not grant temporary access to the specified user.', 401)
    )
    def checkTemporaryPassword(self, user, token):
        token = Token().load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = Token().hasScope(token, TokenScope.TEMPORARY_USER_AUTH)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token does not grant temporary access to this user.')

        # Temp auth is verified, send an actual auth token now. We keep the
        # temp token around since it can still be used on a subsequent request
        # to change the password
        authToken = self.sendAuthTokenCookie(user)

        return {
            'user': self._model.filter(user, user),
            'authToken': {
                'token': authToken['_id'],
                'expires': authToken['expires'],
                'temporary': True
            },
            'message': 'Temporary access token is valid.'
        }

    @access.public
    @autoDescribeRoute(
        Description('Get detailed information about a user.')
        .modelParam('id', model=UserModel, level=AccessType.READ)
        .errorResponse()
        .errorResponse('Read access was denied on the user.', 403)
    )
    def getUserDetails(self, user):
        return {
            'nFolders': self._model.countFolders(
                user, filterUser=self.getCurrentUser(), level=AccessType.READ)
        }

    @access.user
    @autoDescribeRoute(
        Description('Initiate the enablement of one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def initializeOtp(self, user):
        if self._model.hasOtpEnabled(user):
            raise RestException('The user has already enabled one-time passwords.')

        otpUris = self._model.initializeOtp(user)
        self._model.save(user)

        return otpUris

    @access.user
    @autoDescribeRoute(
        Description('Finalize the enablement of one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .param('Girder-OTP', 'A one-time password for this user', paramType='header')
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def finalizeOtp(self, user):
        otpToken = cherrypy.request.headers.get('Girder-OTP')
        if not otpToken:
            raise RestException('The "Girder-OTP" header must be provided.')

        if 'otp' not in user:
            raise RestException('The user has not initialized one-time passwords.')
        if self._model.hasOtpEnabled(user):
            raise RestException('The user has already enabled one-time passwords.')

        user['otp']['enabled'] = True
        # This will raise an exception if the verification fails, so the user will not be saved
        self._model.verifyOtp(user, otpToken)

        self._model.save(user)

    @access.user
    @autoDescribeRoute(
        Description('Disable one-time passwords for this user.')
        .modelParam('id', model=UserModel, level=AccessType.ADMIN)
        .errorResponse()
        .errorResponse('Admin access was denied on the user.', 403)
    )
    def removeOtp(self, user):
        if not self._model.hasOtpEnabled(user):
            raise RestException('The user has not enabled one-time passwords.')

        del user['otp']
        self._model.save(user)

    @access.public
    @autoDescribeRoute(
        Description('Verify an email address using a token.')
        .modelParam('id', 'The user ID to check.', model=UserModel, force=True)
        .param('token', 'The token to check.')
        .errorResponse('The token is invalid or expired.', 401)
    )
    def verifyEmail(self, user, token):
        token = Token().load(
            token, user=user, level=AccessType.ADMIN, objectId=False, exc=True)
        delta = (token['expires'] - datetime.datetime.utcnow()).total_seconds()
        hasScope = Token().hasScope(token, TokenScope.EMAIL_VERIFICATION)

        if token.get('userId') != user['_id'] or delta <= 0 or not hasScope:
            raise AccessException('The token is invalid or expired.')

        user['emailVerified'] = True
        Token().remove(token)
        user = self._model.save(user)

        if self._model.canLogin(user):
            setCurrentUser(user)
            authToken = self.sendAuthTokenCookie(user)
            return {
                'user': self._model.filter(user, user),
                'authToken': {
                    'token': authToken['_id'],
                    'expires': authToken['expires'],
                    'scope': authToken['scope']
                },
                'message': 'Email verification succeeded.'
            }
        else:
            return {
                'user': self._model.filter(user, user),
                'message': 'Email verification succeeded.'
            }

    @access.public
    @autoDescribeRoute(
        Description('Send verification email.')
        .param('login', 'Your login or email address.', strip=True)
        .errorResponse('That login is not registered.', 401)
    )
    def sendVerificationEmail(self, login):
        loginField = 'email' if '@' in login else 'login'
        user = self._model.findOne({loginField: login.lower()})

        if not user:
            raise RestException('That login is not registered.', 401)

        self._model._sendVerificationEmail(user)
        return {'message': 'Sent verification email.'}
