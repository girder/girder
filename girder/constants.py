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
import json

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PACKAGE_DIR)
LOG_ROOT = os.path.join(os.path.expanduser('~'), '.girder', 'logs')
ROOT_PLUGINS_PACKAGE = 'girder.plugins'
MAX_LOG_SIZE = 1024 * 1024 * 10  # Size in bytes before logs are rotated.
LOG_BACKUP_COUNT = 5

# Identifier for Girder's entry in the route table
GIRDER_ROUTE_ID = 'core_girder'
GIRDER_STATIC_ROUTE_ID = 'core_static_root'

# Threshold below which text search results will be sorted by their text score.
# Setting this too high causes mongodb to use too many resources for searches
# that yield lots of results.
TEXT_SCORE_SORT_MAX = 200

# Get the version information
VERSION = {  # Set defaults in case girder-version.json doesn't exist
    'git': False,
    'SHA': None,
    'shortSHA': None,
    'apiVersion': None,
    'date': None
}
try:
    with open(os.path.join(PACKAGE_DIR, 'girder-version.json')) as f:
        VERSION.update(json.load(f))
except IOError:  # pragma: no cover
    pass

#: The local directory containing the static content.
#: Should contain ``clients/web/static``.
STATIC_ROOT_DIR = ROOT_DIR
if not os.path.exists(os.path.join(STATIC_ROOT_DIR, 'clients')):
    STATIC_ROOT_DIR = PACKAGE_DIR


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


class AssetstoreType:
    """
    All possible assetstore implementation types.
    """
    FILESYSTEM = 0
    GRIDFS = 1
    S3 = 2


class AccessType:
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


class SettingKey:
    """
    Core settings should be enumerated here by a set of constants corresponding
    to sensible strings.
    """
    PLUGINS_ENABLED = 'core.plugins_enabled'
    COOKIE_LIFETIME = 'core.cookie_lifetime'
    EMAIL_FROM_ADDRESS = 'core.email_from_address'
    EMAIL_HOST = 'core.email_host'
    REGISTRATION_POLICY = 'core.registration_policy'
    EMAIL_VERIFICATION = 'core.email_verification'
    SMTP_HOST = 'core.smtp_host'
    SMTP_PORT = 'core.smtp.port'
    SMTP_ENCRYPTION = 'core.smtp.encryption'
    SMTP_USERNAME = 'core.smtp.username'
    SMTP_PASSWORD = 'core.smtp.password'
    UPLOAD_MINIMUM_CHUNK_SIZE = 'core.upload_minimum_chunk_size'
    CORS_ALLOW_ORIGIN = 'core.cors.allow_origin'
    CORS_ALLOW_METHODS = 'core.cors.allow_methods'
    CORS_ALLOW_HEADERS = 'core.cors.allow_headers'
    ADD_TO_GROUP_POLICY = 'core.add_to_group_policy'
    COLLECTION_CREATE_POLICY = 'core.collection_create_policy'
    USER_DEFAULT_FOLDERS = 'core.user_default_folders'
    ROUTE_TABLE = 'core.route_table'


class SettingDefault:
    """
    Core settings that have a default should be enumerated here with the
    SettingKey.
    """
    defaults = {
        SettingKey.PLUGINS_ENABLED: [],
        SettingKey.COOKIE_LIFETIME: 180,
        SettingKey.EMAIL_FROM_ADDRESS: 'Girder <no-reply@girder.org>',
        SettingKey.REGISTRATION_POLICY: 'open',
        SettingKey.EMAIL_VERIFICATION: 'disabled',
        SettingKey.SMTP_HOST: 'localhost',
        SettingKey.SMTP_PORT: 25,
        SettingKey.SMTP_ENCRYPTION: 'none',
        SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE: 1024 * 1024 * 5,
        # These headers are necessary to allow the web server to work with just
        # changes to the CORS origin
        SettingKey.CORS_ALLOW_HEADERS:
            'Accept-Encoding, Authorization, Content-Disposition, '
            'Content-Type, Cookie, Girder-Authorization, Girder-Token',
            # An apache server using reverse proxy would also need
            #  X-Requested-With, X-Forwarded-Server, X-Forwarded-For,
            #  X-Forwarded-Host, Remote-Addr
        SettingKey.ADD_TO_GROUP_POLICY: 'never',
        SettingKey.COLLECTION_CREATE_POLICY: {
            'open': False,
            'groups': [],
            'users': []
        },
        SettingKey.USER_DEFAULT_FOLDERS: 'public_private'
    }


class SortDir(object):
    ASCENDING = 1
    DESCENDING = -1


class TokenScope:
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
        else:
            cls._customScopes.append(info)

    @classmethod
    def listScopes(cls):
        return {
            'custom': cls._customScopes,
            'adminCustom': cls._adminCustomScopes
        }

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
