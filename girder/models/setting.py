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

from ..constants import SettingDefault, SettingKey
from .model_base import Model, ValidationException
from girder.utility import camelcase, plugin_utilities


class Setting(Model):
    """
    This model represents server-wide configuration settings as key/value pairs.
    """
    def initialize(self):
        self.name = 'setting'
        self.ensureIndices(['key'])
        self._corsSettingsCache = None

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
        """
        Ensures that the set of plugins passed in is a list of valid plugin
        names. Removes any invalid plugin names, removes duplicates, and adds
        all transitive dependencies to the enabled list.
        """
        if not type(doc['value']) is list:
            raise ValidationException(
                'Plugins enabled setting must be a list.', 'value')

        allPlugins = plugin_utilities.findAllPlugins()
        doc['value'] = set(doc['value'])

        def addDeps(plugin):
            for dep in allPlugins[plugin]['dependencies']:
                if dep not in doc['value']:
                    doc['value'].add(dep)
                addDeps(dep)

        for enabled in list(doc['value']):
            if enabled in allPlugins:
                addDeps(enabled)
            else:
                doc['value'].remove(enabled)

        doc['value'] = list(doc['value'])

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
        if isinstance(doc['value'], basestring):
            methods = doc['value'].replace(",", " ").strip().upper().split()
            # remove duplicates
            methods = list(OrderedDict.fromkeys(methods))
            doc['value'] = ", ".join(methods)
            self.corsSettingsCacheClear()
            return
        raise ValidationException(
            'Allowed methods must be a comma-separated list or an empty '
            'string.', 'value')

    def validateCoreCorsAllowHeaders(self, doc):
        if isinstance(doc['value'], basestring):
            headers = doc['value'].replace(",", " ").strip().split()
            # remove duplicates
            headers = list(OrderedDict.fromkeys(headers))
            doc['value'] = ", ".join(headers)
            self.corsSettingsCacheClear()
            return
        raise ValidationException(
            'Allowed headers must be a comma-separated list or an empty '
            'string.', 'value')

    def validateCoreCorsAllowOrigin(self, doc):
        if isinstance(doc['value'], basestring):
            origins = doc['value'].replace(",", " ").strip().split()
            origins = [origin.rstrip('/') for origin in origins]
            # remove duplicates
            origins = list(OrderedDict.fromkeys(origins))
            doc['value'] = ", ".join(origins)
            self.corsSettingsCacheClear()
            return
        raise ValidationException(
            'Allowed origin must be a comma-separated list of base urls or * '
            'or an empty string.', 'value')

    def validateCoreEmailFromAddress(self, doc):
        if not doc['value']:
            raise ValidationException(
                'Email from address must not be blank.', 'value')

    def validateCoreEmailHost(self, doc):
        if isinstance(doc['value'], basestring):
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
                host += ':{}'.format(cherrypy.request.local.port)
            return host

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

    def corsSettingsCacheClear(self):
        """
        Clear the CORS information we have stored for quick use, forcing it to
        be reloaded the next time it is requested.
        """
        self._corsSettingsCache = None

    def corsSettingsDict(self):
        """Return a dictionary of CORS settings.  This parses the user settings
        into a format that is useful for the REST api.  The dictionary
        contains:

        * allowOrigin: None if no CORS settings are present, or a list of
          allowed origins.  If the list contains '*', all origins are allowed.
        * allowMethods: None if all methods allowed, or a list of allowed
          methods.  Note that regardless of this list, GET, HEAD, and some POST
          methods are always allowed.  These are always upper case.
        * allowHeaders: a set of allowed headers.  This includes the headers
          which are always allowed by CORS.  There are always all lower case.

        :returns: a dictionary as described above.
        """
        if self._corsSettingsCache is None:
            cors = {}
            allowOrigin = self.get(SettingKey.CORS_ALLOW_ORIGIN)
            if not allowOrigin:
                cors['allowOrigin'] = None
            else:
                cors['allowOrigin'] = allowOrigin.replace(",", " ").strip(). \
                    split()
            methods = self.get(SettingKey.CORS_ALLOW_METHODS)
            if not methods:
                cors['allowMethods'] = None
            else:
                cors['allowMethods'] = methods.replace(",", " ").strip(). \
                    upper().split()
            headers = set(self.get(SettingKey.CORS_ALLOW_HEADERS).replace(
                ",", " ").strip().lower().split())
            headers = {header.lower() for header in headers.union({
                'Accept',
                # in defaults: Accept-Encoding
                'Accept-Language',
                # in defaults: Authorization
                # in defaults: Content-Dispostion
                'Connection',
                'Content-Language',
                'Content-Length',
                # Content-Type is in the defaults besides being listed here,
                # because some CORS requests don't have to permit it.  We side
                # on always allowing it, though it may need to be in the
                # allowed headers that are sent to the browser for the browser
                # to be willing to send the CORS request
                'Content-Type',
                # in defaults: Cookie
                # in defaults: Girder-Token
                'Host',
                'Origin',
                'Referer',
                'User-Agent'})}
            cors['allowHeaders'] = headers
            self._corsSettingsCache = cors
        return self._corsSettingsCache
