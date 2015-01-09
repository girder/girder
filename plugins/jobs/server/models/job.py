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

import datetime
import pymongo

from girder import events
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel, ValidationException
from girder.plugins.jobs.constants import JobStatus


class Job(AccessControlledModel):
    def initialize(self):
        self.name = 'job'
        compoundSearchIndex = (
            ('userId', pymongo.ASCENDING),
            ('created', pymongo.DESCENDING)
        )
        self.ensureIndices([(compoundSearchIndex, {})])

    def validate(self, job):
        job['status'] = int(job['status'])

        if not JobStatus.isValid(job['status']):
            raise ValidationException('Invalid job status {}.'.format(
                                      job.get['status']), field='status')

        return job

    def list(self, user=None, limit=50, offset=0, sort=None, currentUser=None):
        """
        List a page of jobs for a given user.

        :param user: The user who owns the job.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        :param currentUser: User for access filtering.
        """
        userId = user['_id'] if user else None
        cursor = self.find({'userId': userId}, limit=0, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=currentUser,
                                                level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def cancelJob(self, job):
        """
        Revoke/cancel a job. This simply triggers the jobs.cancel event and
        sets the job status  to CANCELED. If one of the event handlers
        calls preventDefault() on the event, this job will *not* be put into
        the CANCELED state.

        :param job: The job to cancel.
        """
        event = events.trigger('jobs.cancel', info=job)

        if not event.defaultPrevented:
            job['status'] = JobStatus.CANCELED
            self.save(job)

        return job

    def createJob(self, title, type, args=(), kwargs={}, user=None, when=None,
                  interval=0, public=False, handler=None):
        """
        Create a new job record.

        :param title: The title of the job.
        :type title: str
        :param type: The type of the job.
        :type type: str
        :param args: Positional args of the job payload.
        :type args: list or tuple
        :param kwargs: Keyword arguments of the job payload.
        :type kwargs: dict
        :param user: The user creating the job.
        :type user: dict or None
        :param when: Minimum start time for the job (UTC).
        :type when: datetime
        :param interval: If this job should be recurring, set this to a value
        in seconds representing how often it should occur. Set to <= 0 for
        jobs that should only be run once.
        :type interval: int
        :param public: Public read access flag.
        :type public: bool
        :param handler: If this job should be handled by a specific handler,
        use this field to store that information.
        :param externalToken: If an external token was created for updating this
        job, pass it in and it will have the job-specific scope set.
        :type externalToken: token (dict) or None.
        """
        now = datetime.datetime.utcnow()

        if when is None:
            when = now

        job = {
            'title': title,
            'type': type,
            'args': args,
            'kwargs': kwargs,
            'created': now,
            'updated': now,
            'when': when,
            'interval': interval,
            'status': JobStatus.INACTIVE,
            'progress': None,
            'log': '',
            'meta': {},
            'handler': handler
        }

        self.setPublic(job, public=public)

        if user:
            job['userId'] = user['_id']
            self.setUserAccess(job, user=user, level=AccessType.ADMIN)

        job = self.save(job)

        return job

    def scheduleJob(self, job):
        """
        Trigger the event to schedule this job. Other plugins are in charge of
        actually scheduling and/or executing the job.
        """
        events.trigger('jobs.schedule', info=job)

    def createJobToken(self, job, days=7):
        """
        Create a token that can be used just for the management of an individual
        job, e.g. updating job info, progress, logs, status.
        """
        return self.model('token').createToken(
            days=days, scope='jobs.job_' + str(job['_id']))

    def updateJob(self, job, log=None, overwrite=False, status=None,
                  progressTotal=None, progressCurrent=None, notify=True,
                  progressMessage=None):
        """
        Update an existing job. Any of the updateable fields that are set to
        None in the kwargs will not be modified. If you set progress information
        on the job for the first time and set notify=True, a new notification
        record for the job progress will be created. Job status changes will
        also create a notification with type="job_status" if notify=True.

        :param job: The job document to update.
        :param log: Message to append to the job log. If you wish to overwrite
            instead of append, pass overwrite=True.
        :type log: str
        :param overwrite: Whether to overwrite the log (default is append).
        :type overwrite: bool
        :param status: New status for the job.
        :type status: JobStatus
        :param progressTotal: Max progress value for this job.
        """
        changed = False

        if log is not None:
            changed = True
            if overwrite:
                job['log'] = log
            else:
                job['log'] += log
        if status is not None:
            changed = True
            job['status'] = status

            if notify and job['userId']:
                user = self.model('user').load(job['userId'], force=True)
                expires = expires = (datetime.datetime.utcnow() +
                                     datetime.timedelta(seconds=30))
                self.model('notification').createNotification(
                    type='job_status', data={'status': status}, user=user,
                    expires=expires)
        if (progressMessage is not None or progressCurrent is not None or
                progressTotal is not None):
            changed = True
            self._updateJobProgress(job, progressTotal, progressCurrent,
                                    progressMessage, notify)

        if changed:
            job['updated'] = datetime.datetime.utcnow()
            job = self.save(job)

        return job

    def _updateJobProgress(self, job, total, current, message, notify):
        """Helper for updating job progress information."""
        state = JobStatus.toNotificationStatus(job['status'])

        if job['progress'] is None:
            if notify and job['userId']:
                user = self.model('user').load(job['userId'], force=True)
                # TODO support channel-based notifications for jobs. For
                # right now we'll just go through the user.
                notification = self.model('notification').initProgress(
                    user, job['title'], total, state=state, current=current,
                    message=message, estimateTime=False)
                notificationId = notification['_id']
            else:
                notificationId = None
            job['progress'] = {
                'message': message,
                'total': total,
                'current': current,
                'notificationId': notificationId
            }
        else:
            if total is not None:
                job['progress']['total'] = total
            if current is not None:
                job['progress']['current'] = current
            if message is not None:
                job['progress']['message'] = message

            if notify and job['progress']['notificationId'] is not None:
                notification = self.model('notification').load(
                    job['notificationId'])

                self.model('notification').updateProgress(
                    notification, state=state,
                    message=job['progress']['message'],
                    current=job['progress']['current'],
                    total=job['progress']['total'])

    def filter(self, job, user):
        # Allow downstreams to filter job info as they see fit
        event = events.trigger('jobs.filter', info={
            'job': job,
            'user': user
        })

        keys = ['title', 'type', 'created', 'interval', 'when', 'status',
                'progress', 'log', 'meta', '_id', 'public']

        if user and user['admin'] is True:
            keys.extend(('args', 'kwargs'))

        for resp in event.responses:
            if 'exposeFields' in resp:
                keys.extend(resp['exposeFields'])
            if 'removeFields' in resp:
                keys = [k for k in keys if k not in resp['removeFields']]

        return self.filterDocument(job, allow=keys)
