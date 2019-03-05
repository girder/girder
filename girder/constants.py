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

"""
Constants should be defined here.
"""
import os
import sys

import girder

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PACKAGE_DIR)
LOG_ROOT = os.path.join(os.path.expanduser('~'), '.girder', 'logs')
MAX_LOG_SIZE = 1024 * 1024 * 10  # Size in bytes before logs are rotated.
LOG_BACKUP_COUNT = 5
ACCESS_FLAGS = {}

# Identifier for Girder's entry in the route table
GIRDER_ROUTE_ID = 'core_girder'
GIRDER_STATIC_ROUTE_ID = 'core_static_root'

# Threshold below which text search results will be sorted by their text score.
# Setting this too high causes mongodb to use too many resources for searches
# that yield lots of results.
TEXT_SCORE_SORT_MAX = 200
VERSION = {
    'release': girder.__version__
}

#: The local directory containing the static content.
STATIC_PREFIX = os.path.join(sys.prefix, 'share', 'girder')
STATIC_ROOT_DIR = os.path.join(STATIC_PREFIX, 'static')


def registerAccessFlag(key, name, description=None, admin=False):
    """
    Register a new access flag in the set of ACCESS_FLAGS available
    on data in the hierarchy. These are boolean switches that can be used
    to control access to specific functionality on specific resoruces.

    :param key: The unique identifier for this access flag.
    :type key: str
    :param name: Human readable name for this permission (displayed in UI).
    :type name: str
    :param description: Human readable longer description for the flag.
    :type description: str
    :param admin: Set this to True to only allow site admin users to set
        this flag. If True, the flag will only appear in the list for
        site admins. This can be useful for flags with security
        considerations.
    """
    ACCESS_FLAGS[key] = {
        'name': name,
        'description': description,
        'admin': admin
    }


class TerminalColor(object):
    """
    Provides a set of values that can be used to color text in the terminal.
    """
    ERROR = '\033[1;91m'
    SUCCESS = '\033[32m'
    WARNING = '\033[1;33m'
    INFO = '\033[35m'
    ENDC = '\033[0m'

    @staticmethod
    def _color(tag, text):
        return ''.join([tag, text, TerminalColor.ENDC])

    @staticmethod
    def error(text):
        return TerminalColor._color(TerminalColor.ERROR, text)

    @staticmethod
    def success(text):
        return TerminalColor._color(TerminalColor.SUCCESS, text)

    @staticmethod
    def warning(text):
        return TerminalColor._color(TerminalColor.WARNING, text)

    @staticmethod
    def info(text):
        return TerminalColor._color(TerminalColor.INFO, text)


class AssetstoreType(object):
    """
    All possible assetstore implementation types.
    """
    FILESYSTEM = 0
    GRIDFS = 1
    S3 = 2


class AccessType(object):
    """
    Represents the level of access granted to a user or group on an
    AccessControlledModel. Having a higher access level on a resource also
    confers all of the privileges of the lower levels.

    Semantically, READ access on a resource means that the user can see all
    the information pertaining to the resource, but cannot modify it.

    WRITE access usually means the user can modify aspects of the resource.

    ADMIN access confers total control; the user can delete the resource and
    also manage permissions for other users on it.
    """
    NONE = -1
    READ = 0
    WRITE = 1
    ADMIN = 2
    SITE_ADMIN = 100

    @classmethod
    def validate(cls, level):
        level = int(level)
        if level in (cls.NONE, cls.READ, cls.WRITE, cls.ADMIN, cls.SITE_ADMIN):
            return level
        else:
            raise ValueError('Invalid AccessType: %d.' % level)


class SettingKey(object):
    """
    Core settings should be enumerated here by a set of constants corresponding
    to sensible strings.
    """
    ADD_TO_GROUP_POLICY = 'core.add_to_group_policy'
    API_KEYS = 'core.api_keys'
    BANNER_COLOR = 'core.banner_color'
    BRAND_NAME = 'core.brand_name'
    COLLECTION_CREATE_POLICY = 'core.collection_create_policy'
    PRIVACY_NOTICE = 'core.privacy_notice'
    CONTACT_EMAIL_ADDRESS = 'core.contact_email_address'
    COOKIE_LIFETIME = 'core.cookie_lifetime'
    CORS_ALLOW_HEADERS = 'core.cors.allow_headers'
    CORS_ALLOW_METHODS = 'core.cors.allow_methods'
    CORS_ALLOW_ORIGIN = 'core.cors.allow_origin'
    CORS_EXPOSE_HEADERS = 'core.cors.expose_headers'
    EMAIL_FROM_ADDRESS = 'core.email_from_address'
    EMAIL_HOST = 'core.email_host'
    EMAIL_VERIFICATION = 'core.email_verification'
    ENABLE_PASSWORD_LOGIN = 'core.enable_password_login'
    GIRDER_MOUNT_INFORMATION = 'core.girder_mount_information'
    ENABLE_NOTIFICATION_STREAM = 'core.enable_notification_stream'
    PLUGINS_ENABLED = 'core.plugins_enabled'
    REGISTRATION_POLICY = 'core.registration_policy'
    ROUTE_TABLE = 'core.route_table'
    SECURE_COOKIE = 'core.secure_cookie'
    SERVER_ROOT = 'core.server_root'
    SMTP_ENCRYPTION = 'core.smtp.encryption'
    SMTP_HOST = 'core.smtp_host'
    SMTP_PASSWORD = 'core.smtp.password'
    SMTP_PORT = 'core.smtp.port'
    SMTP_USERNAME = 'core.smtp.username'
    UPLOAD_MINIMUM_CHUNK_SIZE = 'core.upload_minimum_chunk_size'
    USER_DEFAULT_FOLDERS = 'core.user_default_folders'


class SettingDefault(object):
    """
    Core settings that have a default should be enumerated here with the
    SettingKey.
    """
    defaults = {
        SettingKey.ADD_TO_GROUP_POLICY: 'never',
        SettingKey.API_KEYS: True,
        SettingKey.BANNER_COLOR: '#3F3B3B',
        SettingKey.BRAND_NAME: 'Girder',
        SettingKey.COLLECTION_CREATE_POLICY: {
            'open': False,
            'groups': [],
            'users': []
        },
        SettingKey.CONTACT_EMAIL_ADDRESS: 'kitware@kitware.com',
        SettingKey.PRIVACY_NOTICE: 'https://www.kitware.com/privacy',
        SettingKey.COOKIE_LIFETIME: 180,
        # These headers are necessary to allow the web server to work with just
        # changes to the CORS origin
        SettingKey.CORS_ALLOW_HEADERS:
            'Accept-Encoding, Authorization, Content-Disposition, '
            'Content-Type, Cookie, Girder-Authorization, Girder-OTP, Girder-Token',
        SettingKey.CORS_EXPOSE_HEADERS: 'Girder-Total-Count',
        # An apache server using reverse proxy would also need
        #  X-Requested-With, X-Forwarded-Server, X-Forwarded-For,
        #  X-Forwarded-Host, Remote-Addr
        SettingKey.EMAIL_VERIFICATION: 'disabled',
        SettingKey.EMAIL_FROM_ADDRESS: 'Girder <no-reply@girder.org>',
        SettingKey.ENABLE_PASSWORD_LOGIN: True,
        SettingKey.ENABLE_NOTIFICATION_STREAM: True,
        SettingKey.PLUGINS_ENABLED: [],
        SettingKey.REGISTRATION_POLICY: 'open',
        SettingKey.SMTP_HOST: 'localhost',
        SettingKey.SMTP_PORT: 25,
        SettingKey.SMTP_ENCRYPTION: 'none',
        SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE: 1024 * 1024 * 5,
        SettingKey.USER_DEFAULT_FOLDERS: 'public_private'
    }


class SortDir(object):
    ASCENDING = 1
    DESCENDING = -1


class TokenScope(object):
    """
    Constants for core token scope strings. Token scopes must not contain
    spaces, since many services accept scope lists as a space-separated list
    of strings.
    """
    ANONYMOUS_SESSION = 'core.anonymous_session'
    USER_AUTH = 'core.user_auth'
    TEMPORARY_USER_AUTH = 'core.user_auth.temporary'
    EMAIL_VERIFICATION = 'core.email_verification'
    PLUGINS_ENABLED_READ = 'core.plugins.read'
    SETTINGS_READ = 'core.setting.read'
    ASSETSTORES_READ = 'core.assetstore.read'
    PARTIAL_UPLOAD_READ = 'core.partial_upload.read'
    PARTIAL_UPLOAD_CLEAN = 'core.partial_upload.clean'
    DATA_READ = 'core.data.read'
    DATA_WRITE = 'core.data.write'
    DATA_OWN = 'core.data.own'
    USER_INFO_READ = 'core.user_info.read'

    _customScopes = []
    _adminCustomScopes = []
    _scopeIds = set()
    _adminScopeIds = set()

    @classmethod
    def describeScope(cls, scopeId, name, description, admin=False):
        """
        Register a description of a scope.

        :param scopeId: The unique identifier string for the scope.
        :type scopeId: str
        :param name: A short human readable name for the scope.
        :type name: str
        :param description: A more complete description of the scope.
        :type description: str
        :param admin: If this scope only applies to admin users, set to True.
        :type admin: bool
        """
        info = {
            'id': scopeId,
            'name': name,
            'description': description
        }
        if admin:
            cls._adminCustomScopes.append(info)
            cls._adminScopeIds.add(scopeId)
        else:
            cls._customScopes.append(info)
            cls._scopeIds.add(scopeId)

    @classmethod
    def listScopes(cls):
        return {
            'custom': cls._customScopes,
            'adminCustom': cls._adminCustomScopes
        }

    @classmethod
    def scopeIds(cls, admin=False):
        if admin:
            return cls._scopeIds | cls._adminScopeIds
        else:
            return cls._scopeIds


TokenScope.describeScope(
    TokenScope.USER_INFO_READ, 'Read your user information',
    'Allows clients to look up your user information, including private fields '
    'such as email address.')
TokenScope.describeScope(
    TokenScope.DATA_READ, 'Read data',
    'Allows clients to read all data that you have access to.')
TokenScope.describeScope(
    TokenScope.DATA_WRITE, 'Write data',
    'Allows clients to edit data in the hierarchy and create new data anywhere '
    'you have write access.')
TokenScope.describeScope(
    TokenScope.DATA_OWN, 'Data ownership', 'Allows administrative control '
    'on data you own, including setting access control and deletion.'
)

TokenScope.describeScope(
    TokenScope.PLUGINS_ENABLED_READ, 'See enabled plugins', 'Allows clients '
    'to see the list of plugins enabled on the server.', admin=True)
TokenScope.describeScope(
    TokenScope.SETTINGS_READ, 'See system setting values', 'Allows clients to '
    'view the value of any system setting.', admin=True)
TokenScope.describeScope(
    TokenScope.ASSETSTORES_READ, 'View assetstores', 'Allows clients to see '
    'all assetstore information.', admin=True)
TokenScope.describeScope(
    TokenScope.PARTIAL_UPLOAD_READ, 'View unfinished uploads.',
    'Allows clients to see all partial uploads.', admin=True)
TokenScope.describeScope(
    TokenScope.PARTIAL_UPLOAD_CLEAN, 'Remove unfinished uploads.',
    'Allows clients to remove unfinished uploads.', admin=True)


class CoreEventHandler(object):
    """
    This enum represents handler identifier strings for core event handlers.
    If you wish to unbind a core event handler, use one of these as the
    ``handlerName`` argument. Unbinding core event handlers can be used to
    disable certain default functionalities.
    """
    # For removing deleted user/group references from AccessControlledModel
    ACCESS_CONTROL_CLEANUP = 'core.cleanupDeletedEntity'

    # For updating an item's size to include a new file.
    FILE_PROPAGATE_SIZE = 'core.propagateSizeToItem'

    # For adding a group's creator into its ACL at creation time.
    GROUP_CREATOR_ACCESS = 'core.grantCreatorAccess'

    # For creating the default Public and Private folders at user creation time.
    USER_DEFAULT_FOLDERS = 'core.addDefaultFolders'

    # For adding a user into its own ACL.
    USER_SELF_ACCESS = 'core.grantSelfAccess'

    # For updating the cached webroot HTML when settings change.
    WEBROOT_SETTING_CHANGE = 'core.updateWebrootSettings'
