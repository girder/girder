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
import six

from ..constants import SettingDefault
from .model_base import Model, ValidationException
from girder.utility import camelcase, plugin_utilities
from bson.objectid import ObjectId


class Setting(Model):
    """
    This model represents server-wide configuration settings as key/value pairs.
    """
    def initialize(self):
        self.name = 'setting'
        self.ensureIndices(['key'])

    def validate(self, doc):
        """
        This method is in charge of validating that the setting key is a valid
        key, and that for that key, the provided value is valid. It first
        allows plugins to validate the setting, but if none of them can, it
        assumes it is a core setting and does the validation here.
        """
        key = doc['key']

        funcName = 'validate'+camelcase(key)
        if callable(getattr(self, funcName, None)):
            getattr(self, funcName)(doc)
        else:
            raise ValidationException(
                'Invalid setting key "%s".' % key, 'key')

        return doc

    def validateCorePluginsEnabled(self, doc):
        """
        Ensures that the set of plugins passed in is a list of valid plugin
        names. Removes any invalid plugin names, removes duplicates, and adds
        all transitive dependencies to the enabled list.
        """
        if not isinstance(doc['value'], list):
            raise ValidationException(
                'Plugins enabled setting must be a list.', 'value')

        # Add all transitive dependencies and store in toposorted order
        doc['value'] = list(plugin_utilities.getToposortedPlugins(doc['value']))

    def validateCoreAddToGroupPolicy(self, doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('never', 'noadmin', 'nomod', 'yesadmin',
                                'yesmod', ''):
            raise ValidationException(
                'Add to group policy must be one of "never", "noadmin", '
                '"nomod", "yesadmin", or "yesmod".', 'value')

    def validateCoreCollectionCreatePolicy(self, doc):
        value = doc['value']

        if not isinstance(value, dict):
            raise ValidationException('Collection creation policy must be a '
                                      'JSON object.')

        for i, groupId in enumerate(value.get('groups', ())):
            self.model('group').load(groupId, force=True, exc=True)
            value['groups'][i] = ObjectId(value['groups'][i])

        for i, userId in enumerate(value.get('users', ())):
            self.model('user').load(userId, force=True, exc=True)
            value['users'][i] = ObjectId(value['users'][i])

        value['open'] = value.get('open', False)

    def validateCoreCookieLifetime(self, doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException(
            'Cookie lifetime must be an integer > 0.', 'value')

    def validateCoreCorsAllowMethods(self, doc):
        if isinstance(doc['value'], six.string_types):
            methods = doc['value'].replace(",", " ").strip().upper().split()
            # remove duplicates
            methods = list(OrderedDict.fromkeys(methods))
            doc['value'] = ", ".join(methods)
            return
        raise ValidationException(
            'Allowed methods must be a comma-separated list or an empty '
            'string.', 'value')

    def validateCoreCorsAllowHeaders(self, doc):
        if isinstance(doc['value'], six.string_types):
            headers = doc['value'].replace(",", " ").strip().split()
            # remove duplicates
            headers = list(OrderedDict.fromkeys(headers))
            doc['value'] = ", ".join(headers)
            return
        raise ValidationException(
            'Allowed headers must be a comma-separated list or an empty '
            'string.', 'value')

    def validateCoreCorsAllowOrigin(self, doc):
        if isinstance(doc['value'], six.string_types):
            origins = doc['value'].replace(",", " ").strip().split()
            origins = [origin.rstrip('/') for origin in origins]
            # remove duplicates
            origins = list(OrderedDict.fromkeys(origins))
            doc['value'] = ", ".join(origins)
            return
        raise ValidationException(
            'Allowed origin must be a comma-separated list of base urls or * '
            'or an empty string.', 'value')

    def validateCoreEmailFromAddress(self, doc):
        if not doc['value']:
            raise ValidationException(
                'Email from address must not be blank.', 'value')

    def validateCoreEmailHost(self, doc):
        if isinstance(doc['value'], six.string_types):
            doc['value'] = doc['value'].strip()
            return
        raise ValidationException(
            'Email host must be a string.', 'value')

    def defaultCoreEmailHost(self):
        if (cherrypy.request and cherrypy.request.local and
                cherrypy.request.local.name):
            host = '://'.join((cherrypy.request.scheme,
                               cherrypy.request.local.name))
            if cherrypy.request.local.port != 80:
                host += ':%d' % cherrypy.request.local.port
            return host

    def validateCoreRegistrationPolicy(self, doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('open', 'closed', 'approve'):
            raise ValidationException(
                'Registration policy must be "open", "closed", or "approve".',
                'value')

    def validateCoreEmailVerification(self, doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('required', 'optional', 'disabled'):
            raise ValidationException(
                'Email verification must be "required", "optional", or '
                '"disabled".', 'value')

    def validateCoreSmtpHost(self, doc):
        if not doc['value']:
            raise ValidationException(
                'SMTP host must not be blank.', 'value')

    def validateCoreSmtpPort(self, doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException('SMTP port must be an integer > 0.', 'value')

    def validateCoreSmtpEncryption(self, doc):
        if not doc['value'] in ['none', 'starttls', 'ssl']:
            raise ValidationException(
                'SMTP encryption must be one of "none", "starttls", or "ssl".',
                'value')

    def validateCoreSmtpUsername(self, doc):
        # any string is acceptable
        pass

    def validateCoreSmtpPassword(self, doc):
        # any string is acceptable
        pass

    def validateCoreUploadMinimumChunkSize(self, doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] >= 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException(
            'Upload minimum chunk size must be an integer >= 0.',
            'value')

    def validateCoreUserDefaultFolders(self, doc):
        if doc['value'] not in ('public_private', 'none'):
            raise ValidationException(
                'User default folders must be either "public_private" or '
                '"none".', 'value')

    def get(self, key, default='__default__'):
        """
        Retrieve a setting by its key.

        :param key: The key identifying the setting.
        :type key: str
        :param default: If no such setting exists, returns this value instead.
        :returns: The value, or the default value if the key is not found.
        """
        setting = self.findOne({'key': key})
        if setting is None:
            if default is '__default__':
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

        return self.save(setting)

    def unset(self, key):
        """
        Remove the setting for this key. If no such setting exists, this is
        a no-op.

        :param key: The key identifying the setting to be removed.
        :type key: str
        """
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
        default = None
        if key in SettingDefault.defaults:
            default = SettingDefault.defaults[key]
        else:
            funcName = 'default'+camelcase(key)
            if callable(getattr(self, funcName, None)):
                default = getattr(self, funcName)()
        return default
