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

from girder.constants import SettingKey
from .model_base import Model, ValidationException


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
        # TODO allow plugins to intercept the set setting event

        if key == SettingKey.PLUGINS_ENABLED:
            if not type(doc['value']) is list:
                raise ValidationException(
                    'Plugins enabled setting must be a list.', 'value')
        elif key == SettingKey.COOKIE_LIFETIME:
            doc['value'] = int(doc['value'])
            if doc['value'] <= 0:
                raise ValidationException(
                    'Cookie lifetime must be an integer > 0.', 'value')
        elif key == SettingKey.EMAIL_FROM_ADDRESS:
            if not doc['value']:
                raise ValidationException(
                    'Email from address must not be blank.', 'value')
        elif key == SettingKey.SMTP_HOST:
            if not doc['value']:
                raise ValidationException(
                    'SMTP host must not be blank.', 'value')
        else:
            raise ValidationException('Invalid setting key.', 'key')

        return doc

    def get(self, key, default=None):
        """
        Retrieve a setting by its key.

        :param key: The key identifying the setting.
        :type key: str
        :param default: If no such setting exists, returns this value instead.
        :returns: The value, or the default value if the key is not found.
        """
        cursor = self.find({'key': key}, limit=1)
        if cursor.count(True) == 0:
            return default
        else:
            return cursor[0]['value']

    def set(self, key, value):
        """
        Save a setting. If a setting for this key already exists, this will
        replace the existing value.

        :param key: The key identifying the setting.
        :type key: str
        :param value: The object to store for this setting.
        :returns: The document representing the saved Setting.
        """
        cursor = self.find({'key': key}, limit=1)
        if cursor.count(True) == 0:
            doc = {
                'key': key,
                'value': value
            }
        else:
            doc = cursor[0]
            doc['value'] = value

        return self.save(doc)

    def unset(self, key):
        """
        Remove the setting for this key. If no such setting exists, this is
        a no-op.

        :param key: The key identifying the setting to be removed.
        :type key: str
        """
        for setting in self.find({'key': key}):
            self.remove(setting)
