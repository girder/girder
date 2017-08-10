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

from girder.models.model_base import ValidationException
from girder.utility import setting_utilities


# Constants representing the setting keys for this plugin
class PluginSettings:
    GOOGLE_ANALYTICS_TRACKING_ID = 'google_analytics.tracking_id'


@setting_utilities.validator(PluginSettings.GOOGLE_ANALYTICS_TRACKING_ID)
def validateTrackingId(doc):
    if not doc['value']:
        raise ValidationException('Google Analytics Tracking ID must not be empty.', 'value')
