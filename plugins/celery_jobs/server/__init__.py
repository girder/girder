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


def validateSettings(event):
    if event.info['key'] == PluginSettings.BROKER_URL:
        if not event.info['value']:
            raise ValidationException(
                'Celery broker URL must not be empty.', 'value')
        event.preventDefault().stopPropagation()
    if event.info['key'] == PluginSettings.APP_MAIN:
        if not event.info['value']:
            raise ValidationException(
                'Celery app main name must not be empty.', 'value')
        event.preventDefault().stopPropagation()
    if event.info['key'] == PluginSettings.CELERY_USER_ID:
        if not event.info['value']:
            raise ValidationException(
                'Celery user ID must not be empty.', 'value')
        ModelImporter.model('user').load(
            event.info['value'], force=True, exc=True)
        event.preventDefault().stopPropagation()


def getCeleryUser():
    """
    Return the celery user specified as a system setting.
    """
    userId = ModelImporter.model('setting').get(PluginSettings.CELERY_USER_ID)

    if not userId:
        raise Exception('No celery user ID setting present.')
    user = ModelImporter.model('user').load(userId, force=True)

    if not user:
        raise Exception('Celery user does not exist (%s).' % userId)

    return user


def schedule(event):
    settingModel = ModelImporter.model('setting')
    broker = settingModel.get(PluginSettings.BROKER_URL)
    appMain = settingModel.get(PluginSettings.APP_MAIN, 'girder_celery')
    celeryapp = celery.Celery(main=appMain, broker=broker)

    job = event.info
    if job['handler'] == 'celery':
        job['status'] = JobStatus.QUEUED
        ModelImporter.model('job', 'jobs').save(job)
        event.stopPropagation()
        celeryapp.send_task(
            job['type'], job['args'], job['kwargs'])


def load(info):
    events.bind('model.setting.validate', 'celery_jobs', validateSettings)
    events.bind('jobs.schedule', 'celery_jobs', schedule)
