#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

from collections import OrderedDict
import cherrypy
import pymongo
import six
import re

from ..constants import GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID, SettingDefault, SettingKey
from .model_base import Model
from girder import logprint
from girder.exceptions import ValidationException
from girder.plugin import getPlugin
from girder.utility import config, setting_utilities
from girder.utility._cache import cache
from bson.objectid import ObjectId


class Setting(Model):
    """
    This model represents server-wide configuration settings as key/value pairs.
    """
    def initialize(self):
        self.name = 'setting'
        # We had been asking for an index on key, like so:
        #   self.ensureIndices(['key'])
        # We really want the index to be unique, which could be done:
        #   self.ensureIndices([('key', {'unique': True})])
        # We can't do it here, as we have to update and correct older installs,
        # so this is handled in the reconnect method.

    def reconnect(self):
        """
        Reconnect to the database and rebuild indices if necessary.  If a
        unique index on key does not exist, make one, first discarding any
        extant index on key and removing duplicate keys if necessary.
        """
        super(Setting, self).reconnect()
        try:
            indices = self.collection.index_information()
        except pymongo.errors.OperationFailure:
            indices = []
        hasUniqueKeyIndex = False
        presentKeyIndices = []
        for index in indices:
            if indices[index]['key'][0][0] == 'key':
                if indices[index].get('unique'):
                    hasUniqueKeyIndex = True
                    break
                presentKeyIndices.append(index)
        if not hasUniqueKeyIndex:
            for index in presentKeyIndices:
                self.collection.drop_index(index)
            duplicates = self.collection.aggregate([{
                '$group': {'_id': '$key',
                           'key': {'$first': '$key'},
                           'ids': {'$addToSet': '$_id'},
                           'count': {'$sum': 1}}}, {
                '$match': {'count': {'$gt': 1}}}])
            for duplicate in duplicates:
                logprint.warning(
                    'Removing duplicate setting with key %s.' % (
                        duplicate['key']))
                # Remove all of the duplicates.  Keep the item with the lowest
                # id in Mongo.
                for duplicateId in sorted(duplicate['ids'])[1:]:
                    self.collection.delete_one({'_id': duplicateId})
            self.collection.create_index('key', unique=True)

    def validate(self, doc):
        """
        This method is in charge of validating that the setting key is a valid
        key, and that for that key, the provided value is valid. It first
        allows plugins to validate the setting, but if none of them can, it
        assumes it is a core setting and does the validation here.
        """
        key = doc['key']
        validator = setting_utilities.getValidator(key)
        if validator:
            validator(doc)
        else:
            raise ValidationException('Invalid setting key "%s".' % key, 'key')

        return doc

    @cache.cache_on_arguments()
    def _get(self, key):
        """
        This method is so built in caching decorators can be used without specifying
        custom logic for dealing with the default kwarg of self.get.
        """
        return self.findOne({'key': key})

    def get(self, key, default='__default__'):
        """
        Retrieve a setting by its key.

        :param key: The key identifying the setting.
        :type key: str
        :param default: If no such setting exists, returns this value instead.
        :returns: The value, or the default value if the key is not found.
        """
        setting = self._get(key)

        if setting is None:
            if default == '__default__':
                default = self.getDefault(key)
            return default
        else:
            return setting['value']

    def set(self, key, value):
        """
        Save a setting. If a setting for this key already exists, this will
        replace the existing value.

        :param key: The key identifying the setting.
        :type key: str
        :param value: The object to store for this setting.
        :returns: The document representing the saved Setting.
        """
        setting = self.findOne({'key': key})
        if setting is None:
            setting = {
                'key': key,
                'value': value
            }
        else:
            setting['value'] = value

        setting = self.save(setting)

        self._get.set(setting, self, key)

        return setting

    def unset(self, key):
        """
        Remove the setting for this key. If no such setting exists, this is
        a no-op.

        :param key: The key identifying the setting to be removed.
        :type key: str
        """
        self._get.invalidate(self, key)
        for setting in self.find({'key': key}):
            self.remove(setting)

    def getDefault(self, key):
        """
        Retrieve the system default for a value.

        :param key: The key identifying the setting.
        :type key: str
        :returns: The default value if the key is present in both SettingKey
            and referenced in SettingDefault; otherwise None.
        """
        if key in SettingDefault.defaults:
            return SettingDefault.defaults[key]
        else:
            fn = setting_utilities.getDefaultFunction(key)

            if callable(fn):
                return fn()
        return None

    @staticmethod
    @setting_utilities.validator(SettingKey.BRAND_NAME)
    def validateCoreBrandName(doc):
        if not doc['value']:
            raise ValidationException('The brand name may not be empty', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.BANNER_COLOR)
    def validateCoreBannerColor(doc):
        if not doc['value']:
            raise ValidationException('The banner color may not be empty', 'value')
        elif not (re.match(r'^#[0-9A-Fa-f]{6}$', doc['value'])):
            raise ValidationException('The banner color must be a hex color triplet', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.PRIVACY_NOTICE)
    def validateCorePrivacyNotice(doc):
        if not doc['value']:
            raise ValidationException('The privacy notice link may not be empty', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SECURE_COOKIE)
    def validateSecureCookie(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('Secure cookie option must be boolean.', 'value')

    @staticmethod
    @setting_utilities.default(SettingKey.SECURE_COOKIE)
    def defaultSecureCookie():
        return config.getConfig()['server']['mode'] == 'production'

    @staticmethod
    @setting_utilities.validator(SettingKey.PLUGINS_ENABLED)
    def validateCorePluginsEnabled(doc):
        """
        Ensures that the set of plugins passed in is a list of valid plugin
        names. Removes any invalid plugin names, removes duplicates, and adds
        all transitive dependencies to the enabled list.
        """
        if not isinstance(doc['value'], list):
            raise ValidationException('Plugins enabled setting must be a list.', 'value')

        for pluginName in doc['value']:
            if getPlugin(pluginName) is None:
                raise ValidationException('Required plugin %s does not exist.' % pluginName)

    @staticmethod
    @setting_utilities.validator(SettingKey.ADD_TO_GROUP_POLICY)
    def validateCoreAddToGroupPolicy(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('never', 'noadmin', 'nomod', 'yesadmin', 'yesmod', ''):
            raise ValidationException(
                'Add to group policy must be one of "never", "noadmin", '
                '"nomod", "yesadmin", or "yesmod".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.COLLECTION_CREATE_POLICY)
    def validateCoreCollectionCreatePolicy(doc):
        from .group import Group
        from .user import User

        value = doc['value']

        if not isinstance(value, dict):
            raise ValidationException('Collection creation policy must be a JSON object.')

        for i, groupId in enumerate(value.get('groups', ())):
            Group().load(groupId, force=True, exc=True)
            value['groups'][i] = ObjectId(value['groups'][i])

        for i, userId in enumerate(value.get('users', ())):
            User().load(userId, force=True, exc=True)
            value['users'][i] = ObjectId(value['users'][i])

        value['open'] = value.get('open', False)

    @staticmethod
    @setting_utilities.validator(SettingKey.COOKIE_LIFETIME)
    def validateCoreCookieLifetime(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('Cookie lifetime must be an integer > 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SERVER_ROOT)
    def validateCoreServerRoot(doc):
        val = doc['value']
        if val and not val.startswith('http://') and not val.startswith('https://'):
            raise ValidationException('Server root must start with http:// or https://.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_METHODS)
    def validateCoreCorsAllowMethods(doc):
        if isinstance(doc['value'], six.string_types):
            methods = doc['value'].replace(',', ' ').strip().upper().split()
            # remove duplicates
            methods = list(OrderedDict.fromkeys(methods))
            doc['value'] = ', '.join(methods)
            return
        raise ValidationException(
            'Allowed methods must be a comma-separated list or an empty string.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_HEADERS)
    def validateCoreCorsAllowHeaders(doc):
        if isinstance(doc['value'], six.string_types):
            headers = doc['value'].replace(",", " ").strip().split()
            # remove duplicates
            headers = list(OrderedDict.fromkeys(headers))
            doc['value'] = ", ".join(headers)
            return
        raise ValidationException(
            'Allowed headers must be a comma-separated list or an empty string.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_ALLOW_ORIGIN)
    def validateCoreCorsAllowOrigin(doc):
        if isinstance(doc['value'], six.string_types):
            origins = doc['value'].replace(",", " ").strip().split()
            origins = [origin.rstrip('/') for origin in origins]
            # remove duplicates
            origins = list(OrderedDict.fromkeys(origins))
            doc['value'] = ", ".join(origins)
            return
        raise ValidationException(
            'Allowed origin must be a comma-separated list of base urls or * or an empty string.',
            'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CORS_EXPOSE_HEADERS)
    def validateCoreCorsExposeHeaders(doc):
        if not isinstance(doc['value'], six.string_types):
            raise ValidationException('CORS exposed headers must be a string')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_FROM_ADDRESS)
    def validateCoreEmailFromAddress(doc):
        if not doc['value']:
            raise ValidationException('Email from address must not be blank.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.CONTACT_EMAIL_ADDRESS)
    def validateCoreContactEmailAddress(doc):
        if not doc['value']:
            raise ValidationException('Contact email address must not be blank.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_HOST)
    def validateCoreEmailHost(doc):
        if isinstance(doc['value'], six.string_types):
            doc['value'] = doc['value'].strip()
            return
        raise ValidationException('Email host must be a string.', 'value')

    @staticmethod
    @setting_utilities.default(SettingKey.EMAIL_HOST)
    def defaultCoreEmailHost():
        if cherrypy.request and cherrypy.request.local and cherrypy.request.local.name:
            host = '%s://%s' % (cherrypy.request.scheme, cherrypy.request.local.name)
            if cherrypy.request.local.port != 80:
                host += ':%d' % cherrypy.request.local.port
            return host

    @staticmethod
    @setting_utilities.validator(SettingKey.REGISTRATION_POLICY)
    def validateCoreRegistrationPolicy(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('open', 'closed', 'approve'):
            raise ValidationException(
                'Registration policy must be "open", "closed", or "approve".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.EMAIL_VERIFICATION)
    def validateCoreEmailVerification(doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('required', 'optional', 'disabled'):
            raise ValidationException(
                'Email verification must be "required", "optional", or "disabled".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.API_KEYS)
    def validateApiKeys(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('API key setting must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.ENABLE_PASSWORD_LOGIN)
    def validateEnablePasswordLogin(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException('Enable password login setting must be boolean.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.ROUTE_TABLE)
    def validateCoreRouteTable(doc):
        nonEmptyRoutes = [route for route in doc['value'].values() if route]
        for key in [GIRDER_ROUTE_ID, GIRDER_STATIC_ROUTE_ID]:
            if key not in doc['value'] or not doc['value'][key]:
                raise ValidationException('Girder and static root must be routable.')

        for key in doc['value']:
            if (key != GIRDER_STATIC_ROUTE_ID and doc['value'][key] and
                    not doc['value'][key].startswith('/')):
                raise ValidationException('Routes must begin with a forward slash.')
        if doc['value'].get(GIRDER_STATIC_ROUTE_ID):
            if (not doc['value'][GIRDER_STATIC_ROUTE_ID].startswith('/') and
                    '://' not in doc['value'][GIRDER_STATIC_ROUTE_ID]):
                raise ValidationException(
                    'Static root must begin with a forward slash or contain a URL scheme.')

        if len(nonEmptyRoutes) > len(set(nonEmptyRoutes)):
            raise ValidationException('Routes must be unique.')

    @staticmethod
    @setting_utilities.default(SettingKey.ROUTE_TABLE)
    def defaultCoreRouteTable():
        return {
            GIRDER_ROUTE_ID: '/',
            GIRDER_STATIC_ROUTE_ID: '/static'
        }

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_HOST)
    def validateCoreSmtpHost(doc):
        if not doc['value']:
            raise ValidationException('SMTP host must not be blank.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_PORT)
    def validateCoreSmtpPort(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('SMTP port must be an integer > 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_ENCRYPTION)
    def validateCoreSmtpEncryption(doc):
        if not doc['value'] in ['none', 'starttls', 'ssl']:
            raise ValidationException(
                'SMTP encryption must be one of "none", "starttls", or "ssl".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_USERNAME)
    def validateCoreSmtpUsername(doc):
        # any string is acceptable
        pass

    @staticmethod
    @setting_utilities.validator(SettingKey.SMTP_PASSWORD)
    def validateCoreSmtpPassword(doc):
        # any string is acceptable
        pass

    @staticmethod
    @setting_utilities.validator(SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE)
    def validateCoreUploadMinimumChunkSize(doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] >= 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('Upload minimum chunk size must be an integer >= 0.', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.USER_DEFAULT_FOLDERS)
    def validateCoreUserDefaultFolders(doc):
        if doc['value'] not in ('public_private', 'none'):
            raise ValidationException(
                'User default folders must be either "public_private" or "none".', 'value')

    @staticmethod
    @setting_utilities.validator(SettingKey.GIRDER_MOUNT_INFORMATION)
    def validateCoreGirderMountInformation(doc):
        value = doc['value']
        if not isinstance(value, dict) or 'path' not in value:
            raise ValidationException(
                'Girder mount information must be a dict with the "path" key.')

    @staticmethod
    @setting_utilities.validator(SettingKey.ENABLE_NOTIFICATION_STREAM)
    def validateEnableNotificationStream(doc):
        if not isinstance(doc['value'], bool):
            raise ValidationException(
                'Enable notification stream option must be boolean.', 'value')
