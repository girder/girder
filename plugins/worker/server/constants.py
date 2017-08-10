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


# The path that will be mounted in docker containers for data IO
DOCKER_DATA_VOLUME = '/mnt/girder_worker/data'

# The path that will be mounted in docker containers for utility scripts
DOCKER_SCRIPTS_VOLUME = '/mnt/girder_worker/scripts'


# Settings where plugin information is stored
class PluginSettings(object):
    BROKER = 'worker.broker'
    BACKEND = 'worker.backend'
    API_URL = 'worker.api_url'


@setting_utilities.default({
    PluginSettings.BROKER,
    PluginSettings.BACKEND
})
def _defaultBrokerBackend():
    return 'amqp://guest@localhost/'


@setting_utilities.validator({
    PluginSettings.BROKER,
    PluginSettings.BACKEND
})
def _validateBrokerBackend(doc):
    """
    Handle plugin-specific system settings. Right now we don't do any
    validation for the broker or backend URL settings, but we do reinitialize
    the celery app object with the new values.
    """
    global _celeryapp
    _celeryapp = None


@setting_utilities.validator(PluginSettings.API_URL)
def _validateApiUrl(doc):
    val = doc['value']
    if val and not val.startswith('http://') and not val.startswith('https://'):
        raise ValidationException('API URL must start with http:// or https://.', 'value')
