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

import six

from girder import events
from girder.constants import AccessType, SettingDefault
from girder.models.model_base import ValidationException
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

from .constants import PluginSettings, PluginSettingsDefaults
from .rest import getLicenses


def validateString(value):
    """
    Make sure a value is a unicode string.

    :param value: the value to coerce into a unicode string if it isn't already.
    :returns: the unicode string version of the value.
    """
    if value is None:
        value = six.u('')
    if not isinstance(value, six.text_type):
        value = six.text_type(value)
    return value


def updateItemLicense(event):
    """
    REST event handler to update item with license parameter, if provided.
    """
    params = event.info['params']
    if 'license' not in params:
        return

    itemModel = ModelImporter.model('item')
    item = itemModel.load(event.info['returnVal']['_id'], force=True,
                          exc=True)
    newLicense = validateString(params['license'])
    if item['license'] == newLicense:
        return

    # Ensure that new license name is in configured list of licenses.
    #
    # Enforcing this here, instead of when validating the item, avoids an extra
    # database lookup (for the settings) on every future item save.
    if newLicense:
        licenseSetting = ModelImporter.model('setting').get(
            PluginSettings.LICENSES)
        validLicense = any(
            license['name'] == newLicense
            for group in licenseSetting
            for license in group['licenses'])
        if not validLicense:
            raise ValidationException(
                'License name must be in configured list of licenses.',
                'license')

    item['license'] = newLicense
    item = itemModel.save(item)
    event.preventDefault()
    event.addResponse(item)


def postItemAfter(event):
    updateItemLicense(event)


def postItemCopyAfter(event):
    updateItemLicense(event)


def putItemAfter(event):
    updateItemLicense(event)


def validateItem(event):
    item = event.info
    item['license'] = validateString(item.get('license', None))


@setting_utilities.validator(PluginSettings.LICENSES)
def validateLicenses(doc):
    val = doc['value']
    if not isinstance(val, list):
        raise ValidationException('Licenses setting must be a list.', 'value')
    for item in val:
        category = item.get('category', None)
        if not category or not isinstance(category, six.string_types):
            raise ValidationException(
                'License category is required and must be a non-empty string.', 'category')
        licenses = item.get('licenses', None)
        if not isinstance(licenses, list):
            raise ValidationException('Licenses in category must be a list.', 'licenses')
        for license in licenses:
            if not isinstance(license, dict):
                raise ValidationException('License must be a dict.', 'license')
            name = license.get('name', None)
            if not name or not isinstance(name, six.string_types):
                raise ValidationException(
                    'License name is required and must be a non-empty string.', 'name')


def load(info):
    # Bind REST events
    events.bind('rest.post.item.after', 'item_licenses', postItemAfter)
    events.bind('rest.post.item/:id/copy.after', 'item_licenses', postItemCopyAfter)
    events.bind('rest.put.item/:id.after', 'item_licenses', putItemAfter)

    # Bind validation events
    events.bind('model.item.validate', 'item_licenses', validateItem)

    # Add license field to item model
    ModelImporter.model('item').exposeFields(level=AccessType.READ, fields='license')

    # Add endpoint to get list of licenses
    info['apiRoot'].item.route('GET', ('licenses',), getLicenses)

    # Add default license settings
    SettingDefault.defaults[PluginSettings.LICENSES] = \
        PluginSettingsDefaults.defaults[PluginSettings.LICENSES]
