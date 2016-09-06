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
from girder.constants import AccessType
from girder.plugins.jobs.constants import JobStatus
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

_celeryapp = None


class PluginSettings(object):
    BROKER = 'worker.broker'
    BACKEND = 'worker.backend'


class CustomJobStatus(object):
    """
    The custom job status flags for the worker.
    """
    FETCHING_INPUT = 820
    CONVERTING_INPUT = 821
    CONVERTING_OUTPUT = 822
    PUSHING_OUTPUT = 823

    @classmethod
    def isValid(cls, status):
        return status in (
            cls.FETCHING_INPUT,
            cls.CONVERTING_INPUT,
            cls.CONVERTING_OUTPUT,
            cls.PUSHING_OUTPUT
        )


def getCeleryApp():
    """
    Lazy loader for the celery app. Reloads anytime the settings are updated.
    """
    global _celeryapp

    if _celeryapp is None:
        settings = ModelImporter.model('setting')
        backend = settings.get(PluginSettings.BACKEND) or 'amqp://guest@localhost/'
        broker = settings.get(PluginSettings.BROKER) or 'amqp://guest@localhost/'
        _celeryapp = celery.Celery('girder_worker', backend=backend, broker=broker)
    return _celeryapp


def schedule(event):
    """
    This is bound to the "jobs.schedule" event, and will be triggered any time
    a job is scheduled. This handler will process any job that has the
    handler field set to "worker_handler".
    """
    job = event.info
    if job['handler'] == 'worker_handler':
        # Stop event propagation since we have taken care of scheduling.
        event.stopPropagation()

        task = job.get('celeryTaskName', 'girder_worker.run')

        # Send the task to celery
        asyncResult = getCeleryApp().send_task(task, job['args'], job['kwargs'])

        # Set the job status to queued and record the task ID from celery.
        ModelImporter.model('job', 'jobs').updateJob(job, status=JobStatus.QUEUED, otherFields={
            'celeryTaskId': asyncResult.task_id
        })


@setting_utilities.validator({
    PluginSettings.BROKER,
    PluginSettings.BACKEND
})
def validateSettings(doc):
    """
    Handle plugin-specific system settings. Right now we don't do any
    validation for the broker or backend URL settings, but we do reinitialize
    the celery app object with the new values.
    """
    global _celeryapp
    _celeryapp = None


def validateJobStatus(event):
    """Allow our custom job status values."""
    if CustomJobStatus.isValid(event.info):
        event.preventDefault().addResponse(True)


def load(info):
    events.bind('jobs.schedule', 'worker', schedule)
    events.bind('jobs.status.validate', 'worker', validateJobStatus)

    ModelImporter.model('job', 'jobs').exposeFields(AccessType.SITE_ADMIN, {'celeryTaskId'})
