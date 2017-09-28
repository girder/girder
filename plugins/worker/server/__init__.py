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
from celery.result import AsyncResult

from girder import events, logger
from girder.constants import AccessType
from girder.models.model_base import ValidationException
from girder.plugins.jobs.constants import JobStatus
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

from .constants import PluginSettings
from .utils import getWorkerApiUrl, jobInfoSpec

_celeryapp = None


class CustomJobStatus(object):
    """
    The custom job status flags for the worker.
    """
    FETCHING_INPUT = 820
    CONVERTING_INPUT = 821
    CONVERTING_OUTPUT = 822
    PUSHING_OUTPUT = 823
    CANCELING = 824

    # valid transitions for worker scheduled jobs
    valid_worker_transitions = {
        JobStatus.QUEUED: [JobStatus.INACTIVE],
        JobStatus.RUNNING: [JobStatus.QUEUED, FETCHING_INPUT],
        FETCHING_INPUT: [JobStatus.RUNNING],
        CONVERTING_INPUT: [JobStatus.RUNNING, FETCHING_INPUT],
        CONVERTING_OUTPUT: [JobStatus.RUNNING],
        PUSHING_OUTPUT: [JobStatus.RUNNING, CONVERTING_OUTPUT],
        CANCELING: [JobStatus.INACTIVE, JobStatus.QUEUED, JobStatus.RUNNING],
        JobStatus.ERROR: [FETCHING_INPUT, CONVERTING_INPUT, CONVERTING_OUTPUT,
                          PUSHING_OUTPUT, CANCELING, JobStatus.QUEUED,
                          JobStatus.RUNNING],
        # The last two are allowed for revoke called from outside Girder
        JobStatus.CANCELED: [CANCELING, JobStatus.QUEUED, JobStatus.RUNNING],
        JobStatus.SUCCESS: [JobStatus.RUNNING, PUSHING_OUTPUT]
    }

    # valid transitions for celery scheduled jobs
    # N.B. We have the extra worker input/output states defined here for when
    # we are running girder_worker.run as a regualar celery task
    valid_celery_transitions = {
        JobStatus.QUEUED: [JobStatus.INACTIVE],
        # Note celery tasks can jump straight from INACTIVE to RUNNING
        JobStatus.RUNNING: [JobStatus.INACTIVE, JobStatus.QUEUED,
                            FETCHING_INPUT],
        FETCHING_INPUT: [JobStatus.RUNNING],
        CONVERTING_INPUT: [JobStatus.RUNNING, FETCHING_INPUT],
        CONVERTING_OUTPUT: [JobStatus.RUNNING],
        PUSHING_OUTPUT: [JobStatus.RUNNING, CONVERTING_OUTPUT],
        CANCELING: [JobStatus.INACTIVE, JobStatus.QUEUED, JobStatus.RUNNING],
        JobStatus.ERROR: [FETCHING_INPUT, CONVERTING_INPUT, CONVERTING_OUTPUT,
                          PUSHING_OUTPUT, CANCELING, JobStatus.QUEUED,
                          JobStatus.RUNNING],
        JobStatus.CANCELED: [CANCELING, JobStatus.INACTIVE, JobStatus.QUEUED,
                             JobStatus.RUNNING],
        JobStatus.SUCCESS: [JobStatus.RUNNING, PUSHING_OUTPUT]
    }

    @classmethod
    def isValid(cls, status):
        return status in (
            cls.FETCHING_INPUT,
            cls.CONVERTING_INPUT,
            cls.CONVERTING_OUTPUT,
            cls.PUSHING_OUTPUT,
            cls.CANCELING
        )

    @classmethod
    def validTransitionsWorker(cls, status):
        return cls.valid_worker_transitions.get(status)

    @classmethod
    def validTransitionsCelery(cls, status):
        return cls.valid_celery_transitions.get(status)


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
        task = job.get('celeryTaskName', 'girder_worker.run')

        # Set the job status to queued
        ModelImporter.model('job', 'jobs').updateJob(job, status=JobStatus.QUEUED)

        # Send the task to celery
        asyncResult = getCeleryApp().send_task(
            task, job['args'], job['kwargs'], queue=job.get('celeryQueue'), headers={
                'jobInfoSpec': jobInfoSpec(job, job.get('token', None)),
                'apiUrl': getWorkerApiUrl()
            })

        # Record the task ID from celery.
        ModelImporter.model('job', 'jobs').updateJob(job, otherFields={
            'celeryTaskId': asyncResult.task_id
        })

        # Stop event propagation since we have taken care of scheduling.
        event.stopPropagation()


def cancel(event):
    """
    This is bound to the "jobs.cancel" event, and will be triggered any time
    a job is canceled. This handler will process any job that has the
    handler field set to "worker_handler".
    """
    job = event.info
    if job['handler'] in ['worker_handler', 'celery_handler']:
        # Stop event propagation and prevent default, we are using a custom state
        event.stopPropagation().preventDefault()

        celeryTaskId = job.get('celeryTaskId')

        if celeryTaskId is None:
            msg = ("Unable to cancel Celery task. Job '%s' doesn't have a Celery task id."
                   % job['_id'])
            logger.warn(msg)
            return

        if job['status'] not in [CustomJobStatus.CANCELING, JobStatus.CANCELED,
                                 JobStatus.SUCCESS, JobStatus.ERROR]:
            # Set the job status to canceling
            ModelImporter.model('job', 'jobs').updateJob(job, status=CustomJobStatus.CANCELING)

            # Send the revoke request.
            asyncResult = AsyncResult(celeryTaskId, app=getCeleryApp())
            asyncResult.revoke()


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


@setting_utilities.validator({
    PluginSettings.API_URL
})
def validateApiUrl(doc):
    val = doc['value']
    if val and not val.startswith('http://') and not val.startswith('https://'):
        raise ValidationException('API URL must start with http:// or https://.', 'value')


@setting_utilities.validator(PluginSettings.DIRECT_PATH)
def _validateAutoCompute(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('The direct path setting must be true or false.')


def validateJobStatus(event):
    """Allow our custom job status values."""
    if CustomJobStatus.isValid(event.info):
        event.preventDefault().addResponse(True)


def validTransitions(event):
    """Allow our custom job transitions."""
    states = None
    if event.info['job']['handler'] == 'worker_handler':
        states = CustomJobStatus.validTransitionsWorker(event.info['status'])
    elif event.info['job']['handler'] == 'celery_handler':
        states = CustomJobStatus.validTransitionsCelery(event.info['status'])
    if states is not None:
        event.preventDefault().addResponse(states)


def attachParentJob(event):
    """Attach parentJob before a model is saved."""
    jobModel = ModelImporter.model('job', 'jobs')
    job = event.info
    if job.get('celeryParentTaskId'):
        celeryParentTaskId = job['celeryParentTaskId']
        parentJob = jobModel.findOne({'celeryTaskId': celeryParentTaskId})
        event.info['parentId'] = parentJob['_id']


def attachJobInfoSpec(event):
    """Attach jobInfoSpec after a model is saved."""
    jobModel = ModelImporter.model('job', 'jobs')
    job = event.info
    # Local jobs have a module key
    if not job.get('module'):
        jobModel.updateJob(job, otherFields={'jobInfoSpec': jobInfoSpec(job)})


def load(info):
    events.bind('jobs.schedule', 'worker', schedule)
    events.bind('jobs.status.validate', 'worker', validateJobStatus)
    events.bind('jobs.status.validTransitions', 'worker', validTransitions)
    events.bind('jobs.cancel', 'worker', cancel)
    events.bind('model.job.save.after', 'worker', attachJobInfoSpec)
    events.bind('model.job.save', 'worker', attachParentJob)
    ModelImporter.model('job', 'jobs').exposeFields(
        AccessType.SITE_ADMIN, {'celeryTaskId', 'celeryQueue'})
