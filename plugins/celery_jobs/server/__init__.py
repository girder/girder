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

import celery

from girder import events
from girder.models.model_base import ValidationException
from girder.utility.model_importer import ModelImporter
from girder.plugins.jobs.constants import JobStatus
from .constants import PluginSettings

celeryapp = None


def validateSettings(event):
    global celeryapp
    if event.info['key'] == PluginSettings.BROKER_URL:
        if not event.info['value']:
            raise ValidationException(
                'Celery broker URL must not be empty.', 'value')
        celeryapp = None
        event.preventDefault().stopPropagation()
    if event.info['key'] == PluginSettings.APP_MAIN:
        if not event.info['value']:
            raise ValidationException(
                'Celery app main name must not be empty.', 'value')
        celeryapp = None
        event.preventDefault().stopPropagation()


def schedule(event):
    global celeryapp
    if celeryapp is None:
        settingModel = ModelImpoter.model('setting')
        broker = settingModel.get(PluginSettings.BROKER_URL)
        appMain = settingModel.get(PluginSettings.APP_MAIN, 'girder_celery')
        celeryapp = celery.Celery(main=appMain, broker=broker)

    job = event.info
    if job['handler'] == 'celery':
        job['status'] = JobStatus.QUEUED
        ModelImporter.model('job').save(job)
        event.stopPropagation()
        celeryapp.send_task(
            'girder_celery.' + job['type'], job['args'], job['kwargs'])


def load(info):
    events.bind('model.setting.validate', 'oauth', validateSettings)
    events.bind('jobs.create', 'celery_jobs', schedule)
