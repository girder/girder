# -*- coding: utf-8 -*-
import cherrypy
import hashlib

from girder import events
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.models.model_base import AccessType
from girder.models.setting import Setting
from girder.models.user import User
from girder.plugin import GirderPlugin

from .settings import PluginSettings


def computeBaseUrl(user):
    """
    Compute the base gravatar URL for a user and return it. For the moment, the
    current default image is cached in this URL. It is the caller's
    responsibility to save this value on the user document.
    """
    defaultImage = Setting().get(PluginSettings.DEFAULT_IMAGE)

    md5 = hashlib.md5(user['email'].encode('utf8')).hexdigest()
    return 'https://www.gravatar.com/avatar/%s?d=%s' % (md5, defaultImage)


@access.public
@autoDescribeRoute(
    Description('Redirects to the gravatar image for a user.')
    .modelParam('id', 'The ID of the user.', model=User, level=AccessType.READ)
    .param('size', 'Size in pixels for the image (default=64).', required=False,
           dataType='int', default=64)
)
def getGravatar(user, size):
    if not user.get('gravatar_baseUrl'):
        # the save hook will cause the gravatar base URL to be computed
        user = User().save(user)

    raise cherrypy.HTTPRedirect(user['gravatar_baseUrl'] + '&s=%d' % size)


def _userUpdate(event):
    """
    Called when the user document is being changed. We update the cached
    gravatar URL.
    """
    event.info['gravatar_baseUrl'] = computeBaseUrl(event.info)


class GravatarPlugin(GirderPlugin):
    DISPLAY_NAME = 'Gravatar Portraits'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        info['apiRoot'].user.route('GET', (':id', 'gravatar'), getGravatar)

        User().exposeFields(level=AccessType.READ, fields='gravatar_baseUrl')

        events.bind('model.user.save', 'gravatar', _userUpdate)
