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
from girder.models.model_base import AccessControlledModel
from .constants import JobStatus


class Job(AccessControlledModel):
    def initialize(self):
        self.name = 'job'
        self.ensureIndices([([('userId', 1), ('created', 1)], {})])

    def validate(self, job):
        return job

    def createJob(self, title, type, payload, user=None, when=None, interval=0,
                  public=False):
        """
        Create a new job record. This method triggers a jobs.create event that
        job schedulers should listen to in order to schedule the job.

        :param title: The title of the job.
        :type title: str
        :param type: The type of the job.
        :type type: str
        :param payload: The object that will be passed to the job executor.
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
        """
        if when is None:
            when = datetime.datetime.utcnow()

        job = {
            'title': title,
            'type': type,
            'payload': payload,
            'created': datetime.datetime.utcnow(),
            'when': when,
            'interval': interval,
            'status': JobStatus.INACTIVE,
            'progress': None,
            'log': None
        }

        self.setPublic(job, public=public)

        if user:
            job['userId'] = user['_id']
            self.setUserAccess(job, user=user, level=AccessType.ADMIN)

        job = self.save(job)
        events.trigger('jobs.create', info=job)

        return job
