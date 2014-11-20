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

from girder import events
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel, ValidationException
from girder.plugins.jobs.constants import JobStatus


class Job(AccessControlledModel):
    def initialize(self):
        self.name = 'job'
        self.ensureIndices([([('userId', 1), ('created', 1)], {})])

    def validate(self, job):
        job['status'] = int(job['status'])

        if not JobStatus.isValid(job['status']):
            raise ValidationException('Invalid job status {}.'.format(
                                      job.get['status']), field='status')

        return job

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
        if when is None:
            when = datetime.datetime.utcnow()

        job = {
            'title': title,
            'type': type,
            'args': args,
            'kwargs': kwargs,
            'created': datetime.datetime.utcnow(),
            'when': when,
            'interval': interval,
            'status': JobStatus.INACTIVE,
            'progress': None,
            'log': '',
            'extra': {},
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

    def updateJob(self, job, log=None, overwrite=False, status=None):
        """
        Update an existing job.
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

        if changed:
            job = self.save(job)

        return job

    def filter(self, job, user):
        # TODO refine?
        keys = ('title', 'type', 'args', 'kwargs', 'created', 'interval',
                'when', 'status', 'progress', 'log', 'extra')
        return self.filterDocument(job, allow=keys)
