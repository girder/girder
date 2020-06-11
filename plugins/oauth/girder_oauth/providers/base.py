# -*- coding: utf-8 -*-
import json
import re
import requests

from girder.exceptions import RestException, ValidationException
from girder.models.setting import Setting
from girder.models.user import User
from girder.settings import SettingKey

from ..settings import PluginSettings


class ProviderBase:
    _AUTH_SCOPES = []

    def __init__(self, redirectUri, clientId=None, clientSecret=None):
        """
        Base class for OAuth2 providers. The purpose of these classes is to
        perform the user information lookup to their respective provider
        services in order to return a Girder user given an OAuth2 code that was
        sent to us via a callback.

        :param clientId: The client ID for the given OAuth2 provider.
        :type clientId: str
        :param clientSecret: The client secret for the given OAuth2 provider.
        :type clientSecret: str
        :param redirectUri: The redirect URI used in this OAuth2 flow.
        :type redirectUri: str
        """
        self.clientId = clientId or self.getClientIdSetting()
        self.clientSecret = clientSecret or self.getClientSecretSetting()
        self.redirectUri = redirectUri

    @classmethod
    def getProviderName(cls, external=False):
        providerName = cls.__name__
        if external:
            return providerName
        else:
            return providerName.lower()

    def getClientIdSetting(self):
        raise NotImplementedError()

    def getClientSecretSetting(self):
        raise NotImplementedError()

    @classmethod
    def getUrl(cls, state):
        """
        Return the URL to start the OAuth2 authentication flow with an external
        provider.

        This abstract function must be reimplemented by each provider.

        :param state: A unique string, used to prevent CSRF and store other
        state information. This string should not be URL-encoded (that must be
        done in this method).
        :return: An external absolute URL to the start point for this provider's
        OAuth2 flow.
        """
        raise NotImplementedError()

    def getToken(self, code):
        raise NotImplementedError()

    def getUser(self, token):
        """
        Returns a user via this OAuth2 provider, given an OAuth2 access token.

        Subclasses must implement this to retrieve a provider-specific unique
        identifier, email address, first name, last name, and optionally a
        login name from the OAuth2 provider, and then call
        self._createOrReuseUser with that information to lookup or create a
        corresponding Girder user.

        :param token: The current OAuth2 access token.
        :returns: The user document corresponding to this user.
        """
        raise NotImplementedError()

    @classmethod
    def addScopes(cls, scopes):
        """
        Plugins wishing to use additional provider features that require other auth
        scopes should use this method to add additional required scopes to the list.

        :param scopes: List of additional required scopes.
        :type scopes: list
        :returns: The new list of auth scopes.
        """
        cls._AUTH_SCOPES.extend(scopes)
        return cls._AUTH_SCOPES

    @staticmethod
    def _getJson(**kwargs):
        """
        Make an HTTP request using the specified kwargs, then parse it as JSON
        and return the value. If an error occurs, this raises an appropriate
        exception containing the information.
        """
        resp = requests.request(**kwargs)
        content = resp.content

        if isinstance(content, bytes):
            content = content.decode('utf8')

        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise RestException(
                'Got %s code from provider, response="%s".' % (
                    resp.status_code, content
                ), code=502)

        try:
            return json.loads(content)
        except ValueError:
            raise RestException('Non-JSON response: %s' % content, code=502)

    @classmethod
    def _createOrReuseUser(cls, oauthId, email, firstName, lastName,
                           userName=None):
        providerName = cls.getProviderName()

        # Try finding by ID first, since a user can change their email address
        query = {
            # PyMongo may not properly support full embedded document queries,
            # since the object order matters (and Python dicts are unordered),
            # so search by individual embedded fields
            'oauth.provider': providerName,
            'oauth.id': oauthId
        }
        if providerName == 'google':
            # The Google provider was previously stored as capitalized, and
            # legacy databases may still have these entries
            query['oauth.provider'] = {'$in': ['google', 'Google']}
        user = User().findOne(query)
        setId = not user

        # Existing users using OAuth2 for the first time will not have an ID
        if not user:
            user = User().findOne({'email': email})

        dirty = False
        # Create the user if it's still not found
        if not user:
            policy = Setting().get(SettingKey.REGISTRATION_POLICY)
            if policy == 'closed':
                ignore = Setting().get(PluginSettings.IGNORE_REGISTRATION_POLICY)
                if not ignore:
                    raise RestException(
                        'Registration on this instance is closed. Contact an '
                        'administrator to create an account for you.')
            login = cls._deriveLogin(email, firstName, lastName, userName)

            user = User().createUser(
                login=login, password=None, firstName=firstName, lastName=lastName, email=email)
        else:
            # Migrate from a legacy format where only 1 provider was stored
            if isinstance(user.get('oauth'), dict):
                user['oauth'] = [user['oauth']]
                dirty = True
            # Update user data from provider
            if email != user['email']:
                user['email'] = email
                dirty = True
            # Don't set names to empty string
            if firstName != user['firstName'] and firstName:
                user['firstName'] = firstName
                dirty = True
            if lastName != user['lastName'] and lastName:
                user['lastName'] = lastName
                dirty = True
        if setId:
            user.setdefault('oauth', []).append(
                {
                    'provider': providerName,
                    'id': oauthId
                })
            dirty = True
        if dirty:
            user = User().save(user)

        return user

    @classmethod
    def _generateLogins(cls, email, firstName, lastName, userName=None):
        """
        Generate a series of reasonable login names for a new user based on
        their basic information sent to us by the provider.
        """
        # If they have a username on the other service, try that
        if userName:
            yield userName
            userName = re.sub(r'[\W_]+', '', userName)
            yield userName

            for i in range(1, 6):
                yield '%s%d' % (userName, i)

        # Next try to use the prefix from their email address
        prefix = email.split('@')[0]
        yield prefix
        yield re.sub(r'[\W_]+', '', prefix)

        # Finally try to use their first and last name
        yield '%s%s' % (firstName, lastName)

        for i in range(1, 6):
            yield '%s%s%d' % (firstName, lastName, i)

    @classmethod
    def _deriveLogin(cls, email, firstName, lastName, userName=None):
        """
        Attempt to automatically create a login name from existing user
        information from OAuth2 providers. Attempts to generate it from the
        username on the provider, the email address, or first and last name. If
        not possible, returns None and it is left to the caller to generate
        their own login for the user or choose to fail.

        :param email: The email address.
        :type email: str
        """
        # Note, the user's OAuth2 ID should never be used to form a login name,
        # as many OAuth2 services consider that to be private data
        for login in cls._generateLogins(email, firstName, lastName, userName):
            login = login.lower()
            if cls._testLogin(login):
                return login

        raise Exception('Could not generate a unique login name for %s (%s %s)'
                        % (email, firstName, lastName))

    @classmethod
    def _testLogin(cls, login):
        """
        When attempting to generate a username, use this to test if the given
        name is valid.
        """
        try:
            User()._validateLogin(login)
        except ValidationException:
            # Still doesn't match regex, we're hosed
            return False

        # See if this is already taken.
        user = User().findOne({'login': login})
        return not user
