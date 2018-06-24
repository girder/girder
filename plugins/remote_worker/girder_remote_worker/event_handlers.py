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

from __future__ import absolute_import

from celery.result import AsyncResult

from girder import logger
from girder.exceptions import ValidationException
from girder.utility import setting_utilities
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from .celery import getCeleryApp
from .constants import PluginSettings
from .status import CustomJobStatus
from .utils import getWorkerApiUrl, jobInfoSpec


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
        Job().updateJob(job, status=JobStatus.QUEUED)

        # Send the task to celery
        asyncResult = getCeleryApp().send_task(
            task, job['args'], job['kwargs'], queue=job.get('celeryQueue'), headers={
                'jobInfoSpec': jobInfoSpec(job, job.get('token', None)),
                'apiUrl': getWorkerApiUrl()
            })

        # Record the task ID from celery.
        Job().updateJob(job, otherFields={
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
            Job().updateJob(job, status=CustomJobStatus.CANCELING)

            # Send the revoke request.
            asyncResult = AsyncResult(celeryTaskId, app=getCeleryApp())
            asyncResult.revoke()


def attachParentJob(event):
    """Attach parentJob before a model is saved."""
    job = event.info
    if job.get('celeryParentTaskId'):
        celeryParentTaskId = job['celeryParentTaskId']
        parentJob = Job().findOne({'celeryTaskId': celeryParentTaskId})
        event.info['parentId'] = parentJob['_id']


def attachJobInfoSpec(event):
    """Attach jobInfoSpec after a model is saved."""
    job = event.info
    # Local jobs have a module key
    if not job.get('module'):
        Job().updateJob(job, otherFields={'jobInfoSpec': jobInfoSpec(job)})
