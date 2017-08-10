#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
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

from girder.models.model_base import ValidationException
from girder.utility import setting_utilities


# Constants representing the setting keys for this plugin
class PluginSettings:
    PROVENANCE_RESOURCES = 'provenance.resources'


@setting_utilities.default(PluginSettings.PROVENANCE_RESOURCES)
def _defaultProvenanceResources():
    return 'item'


@setting_utilities.validator(PluginSettings.PROVENANCE_RESOURCES)
def _validateProvenanceResources(doc):
    val = doc['value']

    if val:
        if not isinstance(val, six.string_types):
            raise ValidationException('Provenance Resources must be a string.', 'value')
        # accept comma or space separated lists
        resources = val.replace(',', ' ').strip().split()
        if 'item' not in resources:
            # Always include item
            resources.append('item')
        # reformat to a comma-separated list
        doc['value'] = ','.join(resources)
