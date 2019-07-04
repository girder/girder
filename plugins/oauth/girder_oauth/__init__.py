# -*- coding: utf-8 -*-
from girder import events
from girder.constants import SortDir
from girder.exceptions import ValidationException
from girder.models.user import User
from girder.plugin import GirderPlugin

from . import rest, providers


def checkOauthUser(event):
    """
    If an OAuth2 user without a password tries to log in with a password, we
    want to give them a useful error message.
    """
    user = event.info['user']
    if user.get('oauth'):
        if isinstance(user['oauth'], dict):
            # Handle a legacy format where only 1 provider (Google) was stored
            prettyProviderNames = 'Google'
        else:
            prettyProviderNames = ', '.join(
                providers.idMap[val['provider']].getProviderName(external=True)
                for val in user['oauth']
            )
        raise ValidationException(
            "You don't have a password. Please log in with %s, or use the "
            'password reset link.' % prettyProviderNames)


class OAuthPlugin(GirderPlugin):
    DISPLAY_NAME = 'OAuth2 login'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        User().ensureIndex((
            (('oauth.provider', SortDir.ASCENDING),
             ('oauth.id', SortDir.ASCENDING)), {}))
        User().reconnect()

        events.bind('no_password_login_attempt', 'oauth', checkOauthUser)

        info['apiRoot'].oauth = rest.OAuth()
