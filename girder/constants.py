"""
Constants should be defined here.
"""
import os

import girder

# TODO turn all these into pathlib.Paths
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PACKAGE_DIR)
ACCESS_FLAGS = {}

# Threshold below which text search results will be sorted by their text score.
# Setting this too high causes mongodb to use too many resources for searches
# that yield lots of results.
TEXT_SCORE_SORT_MAX = 200
VERSION = {
    'release': girder.__version__
}

#: The local directory containing the static content.
STATIC_ROOT_DIR = os.path.join(PACKAGE_DIR, 'web', 'dist')


def registerAccessFlag(key, name, description=None, admin=False):
    """
    Register a new access flag in the set of ACCESS_FLAGS available
    on data in the hierarchy. These are boolean switches that can be used
    to control access to specific functionality on specific resources.

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


class ServerMode:
    PRODUCTION = 'production'
    DEVELOPMENT = 'development'
    TESTING = 'testing'


class AssetstoreType:
    """
    All possible assetstore implementation types.
    """

    FILESYSTEM = 0
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


class SortDir:
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
    PLUGINS_READ = 'core.plugins.read'
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
    TokenScope.PLUGINS_READ, 'See installed plugins', 'Allows clients '
    'to see the list of plugins installed on the server.', admin=True)
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


class CoreEventHandler:
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
