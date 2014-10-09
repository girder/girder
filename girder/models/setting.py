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

from ..constants import SettingDefault
from .model_base import Model, ValidationException
from ..utility import camelcase


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
                'Invalid setting key "{}".'.format(key), 'key')

        return doc

    def validateCorePluginsEnabled(self, doc):
        if not type(doc['value']) is list:
            raise ValidationException(
                'Plugins enabled setting must be a list.', 'value')

    def validateCoreCookieLifetime(self, doc):
        try:
            doc['value'] = int(doc['value'])
            if doc['value'] > 0:
                return
        except ValueError:
            pass  # We want to raise the ValidationException
        raise ValidationException(
            'Cookie lifetime must be an integer > 0.', 'value')

    def validateCoreEmailFromAddress(self, doc):
        if not doc['value']:
            raise ValidationException(
                'Email from address must not be blank.', 'value')

    def validateCoreRegistrationPolicy(self, doc):
        doc['value'] = doc['value'].lower()
        if doc['value'] not in ('open', 'closed'):
            raise ValidationException(
                'Registration policy must be either "open" or "closed".',
                'value')

    def validateCoreSmtpHost(self, doc):
        if not doc['value']:
            raise ValidationException(
                'SMTP host must not be blank.', 'value')

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
        Retreive the system default for a value.

        :param key: The key identifying the setting.
        :type key: str
        :returns: The default value if the key is present in both SettingKey
                  and referenced in SettingDefault; otherwise None.
        """
        default = SettingDefault.defaults.get(key, None)
        return default
