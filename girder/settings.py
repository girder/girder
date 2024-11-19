from collections import OrderedDict

import cherrypy
from bson import ObjectId
import re

from girder.exceptions import ValidationException
from girder.utility import setting_utilities


class SettingKey:
    """
    Core settings should be enumerated here by a set of constants corresponding
    to sensible strings.
    """

    ADD_TO_GROUP_POLICY = 'core.add_to_group_policy'
    API_KEYS = 'core.api_keys'
    BANNER_COLOR = 'core.banner_color'
    BRAND_NAME = 'core.brand_name'
    CACHE_ENABLED = 'core.cache.enabled'
    CACHE_CONFIG = 'core.cache_config'
    COLLECTION_CREATE_POLICY = 'core.collection_create_policy'
    CONTACT_EMAIL_ADDRESS = 'core.contact_email_address'
    COOKIE_LIFETIME = 'core.cookie_lifetime'
    COOKIE_DOMAIN = 'core.cookie_domain'
    CORS_ALLOW_HEADERS = 'core.cors.allow_headers'
    CORS_ALLOW_METHODS = 'core.cors.allow_methods'
    CORS_ALLOW_ORIGIN = 'core.cors.allow_origin'
    CORS_EXPOSE_HEADERS = 'core.cors.expose_headers'
    EMAIL_FROM_ADDRESS = 'core.email_from_address'
    EMAIL_HOST = 'core.email_host'
    EMAIL_VERIFICATION = 'core.email_verification'
    ENABLE_NOTIFICATION_STREAM = 'core.enable_notification_stream'
    ENABLE_PASSWORD_LOGIN = 'core.enable_password_login'
    FILEHANDLE_MAX_SIZE = 'core.filehandle_max_size'
    GIRDER_MOUNT_INFORMATION = 'core.girder_mount_information'
    PRIVACY_NOTICE = 'core.privacy_notice'
    REGISTRATION_POLICY = 'core.registration_policy'
    SERVER_ROOT = 'core.server_root'
    SMTP_ENCRYPTION = 'core.smtp.encryption'
    SMTP_HOST = 'core.smtp_host'
    SMTP_PASSWORD = 'core.smtp.password'
    SMTP_PORT = 'core.smtp.port'
    SMTP_USERNAME = 'core.smtp.username'
    UPLOAD_MINIMUM_CHUNK_SIZE = 'core.upload_minimum_chunk_size'
    USER_DEFAULT_FOLDERS = 'core.user_default_folders'


class SettingDefault:
    """
    Core settings that have a default should be enumerated here with the
    SettingKey.
    """

    defaults = {
        SettingKey.ADD_TO_GROUP_POLICY: 'never',
        SettingKey.API_KEYS: True,
        SettingKey.BANNER_COLOR: '#3F3B3B',
        SettingKey.BRAND_NAME: 'Girder',
        SettingKey.CACHE_ENABLED: False,
        SettingKey.CACHE_CONFIG: {},
        SettingKey.COLLECTION_CREATE_POLICY: {
            'open': False,
            'groups': [],
            'users': []
        },
        SettingKey.CONTACT_EMAIL_ADDRESS: 'kitware@kitware.com',
        SettingKey.COOKIE_LIFETIME: 180,
        SettingKey.COOKIE_DOMAIN: '',
        # These headers are necessary to allow the web server to work with just
        # changes to the CORS origin
        SettingKey.CORS_ALLOW_HEADERS:
            'Accept-Encoding, Authorization, Content-Disposition, '
            'Content-Type, Cookie, Girder-Authorization, Girder-OTP, Girder-Token',
        SettingKey.CORS_ALLOW_METHODS: 'GET, POST, PUT, HEAD, DELETE',
        SettingKey.CORS_ALLOW_ORIGIN: '',
        SettingKey.CORS_EXPOSE_HEADERS: 'Girder-Total-Count, Content-Disposition',
        # An apache server using reverse proxy would also need
        #  X-Requested-With, X-Forwarded-Server, X-Forwarded-For,
        #  X-Forwarded-Host, Remote-Addr
        SettingKey.EMAIL_FROM_ADDRESS: 'Girder <no-reply@girder.org>',
        # SettingKey.EMAIL_HOST is provided by a function
        SettingKey.EMAIL_VERIFICATION: 'disabled',
        SettingKey.ENABLE_NOTIFICATION_STREAM: True,
        SettingKey.ENABLE_PASSWORD_LOGIN: True,
        SettingKey.FILEHANDLE_MAX_SIZE: 1024 * 1024 * 16,
        SettingKey.GIRDER_MOUNT_INFORMATION: None,
        SettingKey.PRIVACY_NOTICE: 'https://www.kitware.com/privacy',
        SettingKey.REGISTRATION_POLICY: 'open',
        SettingKey.SERVER_ROOT: '',
        SettingKey.SMTP_ENCRYPTION: 'none',
        SettingKey.SMTP_HOST: 'localhost',
        SettingKey.SMTP_PASSWORD: '',
        SettingKey.SMTP_PORT: 25,
        SettingKey.SMTP_USERNAME: '',
        SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE: 1024 * 1024 * 5,
        SettingKey.USER_DEFAULT_FOLDERS: 'public_private'
    }

    @staticmethod
    @setting_utilities.default(SettingKey.EMAIL_HOST)
    def _defaultEmailHost():
        if cherrypy.request and cherrypy.request.local and cherrypy.request.local.name:
            host = '%s://%s' % (cherrypy.request.scheme, cherrypy.request.local.name)
            if cherrypy.request.local.port != 80:
                host += ':%d' % cherrypy.request.local.port
            return host


class SettingValidator:
    @staticmethod
    @setting_utilities.validator(SettingKey.ADD_TO_GROUP_POLICY)
    def _validateAddToGroupPolicy(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('never', 'noadmin', 'nomod', 'yesadmin', 'yesmod', ''):
            raise ValidationException(
                'Add to group policy must be one of "never", "noadmin", '
                '"nomod", "yesadmin", or "yesmod".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.API_KEYS)
    def _validateApiKeys(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('API key setting must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.BANNER_COLOR)
    def _validateBannerColor(doc):
        if not doc['value']:
            raise ValidationException('The banner color may not be empty', 'value')
        elif not (re.match(r'^#[0-9A-Fa-f]{6}$', doc['value'])):
            raise ValidationException('The banner color must be a hex color triplet', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.BRAND_NAME)
    def _validateBrandName(doc):
        if not doc['value']:
            raise ValidationException('The brand name may not be empty', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CACHE_ENABLED)
    def _validateCacheEnabled(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('Cache enabled setting must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CACHE_CONFIG)
    def _validateCacheConfig(doc):
        if not isinstance(doc['value'], dict):
            raise ValidationException('Cache config must be a JSON object.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.COLLECTION_CREATE_POLICY)
    def _validateCollectionCreatePolicy(doc):
        from girder.models.group import Group
        from girder.models.user import User

        value = doc['value']

        if not isinstance(value, dict):
            raise ValidationException('Collection creation policy must be a JSON object.', 'value')

        for i, groupId in enumerate(value.get('groups', ())):
            Group().load(groupId, force=True, exc=True)
            value['groups'][i] = ObjectId(value['groups'][i])

        for i, userId in enumerate(value.get('users', ())):
            User().load(userId, force=True, exc=True)
            value['users'][i] = ObjectId(value['users'][i])

        value['open'] = value.get('open', False)

    @staticmethod
    @setting_utilities.validator(SettingKey.CONTACT_EMAIL_ADDRESS)
    def _validateContactEmailAddress(doc):
        # This is typically used within an RFC 6068 "mailto:" scheme, so no display name is allowed
        from girder.utility.mail_utils import validateEmailAddress
        if not validateEmailAddress(doc['value']):
            raise ValidationException(
                'Contact email address must be a valid email address.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.COOKIE_LIFETIME)
    def _validateCookieLifetime(doc):
        try:
            doc['value'] = float(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('Cookie lifetime must be a number > 0.0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.COOKIE_DOMAIN)
    def _validateCookieDomain(doc):
        if not isinstance(doc['value'], str):
            raise ValidationException('Cookie domain must be a string', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_HEADERS)
    def _validateCorsAllowHeaders(doc):
        if isinstance(doc['value'], str):
            headers = doc['value'].replace(',', ' ').strip().split()
            # remove duplicates
            headers = list(OrderedDict.fromkeys(headers))
            doc['value'] = ', '.join(headers)
            return
        raise ValidationException(
            'Allowed headers must be a comma-separated list or an empty string.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_METHODS)
    def _validateCorsAllowMethods(doc):
        if isinstance(doc['value'], str):
            methods = doc['value'].replace(',', ' ').strip().upper().split()
            # remove duplicates
            methods = list(OrderedDict.fromkeys(methods))
            doc['value'] = ', '.join(methods)
            return
        raise ValidationException(
            'Allowed methods must be a comma-separated list or an empty string.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_ORIGIN)
    def _validateCorsAllowOrigin(doc):
        if isinstance(doc['value'], str):
            origins = doc['value'].replace(',', ' ').strip().split()
            origins = [origin.rstrip('/') for origin in origins]
            # remove duplicates
            origins = list(OrderedDict.fromkeys(origins))
            doc['value'] = ', '.join(origins)
            return
        raise ValidationException(
            'Allowed origin must be a comma-separated list of base urls or * or an empty string.',
            'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_EXPOSE_HEADERS)
    def _validateCorsExposeHeaders(doc):
        if not isinstance(doc['value'], str):
            raise ValidationException('CORS exposed headers must be a string', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_FROM_ADDRESS)
    def _validateEmailFromAddress(doc):
        # mail_utils.validateEmailAddress cannot be used here, as RFC 5322 allows this to accept an
        # an address which includes a display name too
        if not doc['value']:
            raise ValidationException('Email from address must not be blank.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_HOST)
    def _validateEmailHost(doc):
        if isinstance(doc['value'], str):
            doc['value'] = doc['value'].strip()
            return
        raise ValidationException('Email host must be a string.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_VERIFICATION)
    def _validateEmailVerification(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('required', 'optional', 'disabled'):
            raise ValidationException(
                'Email verification must be "required", "optional", or "disabled".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.ENABLE_NOTIFICATION_STREAM)
    def _validateEnableNotificationStream(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('Enable notification stream option must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.ENABLE_PASSWORD_LOGIN)
    def _validateEnablePasswordLogin(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('Enable password login setting must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.FILEHANDLE_MAX_SIZE)
    def _validateFilehandleMaxSize(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] >= 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException(
            'Maximum file size for filehandle must be an integer >= 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.GIRDER_MOUNT_INFORMATION)
    def _validateGirderMountInformation(doc):
        value = doc['value']
        if not isinstance(value, dict) or 'path' not in value:
            raise ValidationException(
                'Girder mount information must be a dict with the "path" key.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.PRIVACY_NOTICE)
    def _validatePrivacyNotice(doc):
        if not doc['value']:
            raise ValidationException('The privacy notice link may not be empty', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.REGISTRATION_POLICY)
    def _validateRegistrationPolicy(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('open', 'closed', 'approve'):
            raise ValidationException(
                'Registration policy must be "open", "closed", or "approve".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SERVER_ROOT)
    def _validateServerRoot(doc):
        val = doc['value']
        if val and not val.startswith('http://') and not val.startswith('https://'):
            raise ValidationException('Server root must start with http:// or https://.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_ENCRYPTION)
    def _validateSmtpEncryption(doc):
        if not doc['value'] in ['none', 'starttls', 'ssl']:
            raise ValidationException(
                'SMTP encryption must be one of "none", "starttls", or "ssl".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_HOST)
    def _validateSmtpHost(doc):
        if not doc['value']:
            raise ValidationException('SMTP host must not be blank.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_PASSWORD)
    def _validateSmtpPassword(doc):
        if not isinstance(doc['value'], str):
            raise ValidationException('SMTP password must be a string', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_PORT)
    def _validateSmtpPort(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('SMTP port must be an integer > 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_USERNAME)
    def _validateSmtpUsername(doc):
        if not isinstance(doc['value'], str):
            raise ValidationException('SMTP username must be a string', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE)
    def _validateUploadMinimumChunkSize(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] >= 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('Upload minimum chunk size must be an integer >= 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.USER_DEFAULT_FOLDERS)
    def _validateUserDefaultFolders(doc):
        if doc['value'] not in ('public_private', 'none'):
            raise ValidationException(
                'User default folders must be either "public_private" or "none".', 'value')
