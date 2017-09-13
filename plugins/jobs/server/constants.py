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

from girder import events
from girder.models.notification import ProgressState

JOB_HANDLER_LOCAL = 'jobs._local'


# Scope used allow RESTful creation of girder job models
REST_CREATE_JOB_TOKEN_SCOPE = 'jobs.rest.create_job'


# integer enum describing job states. Note, no order is implied.
class JobStatus(object):
    INACTIVE = 0
    QUEUED = 1
    RUNNING = 2
    SUCCESS = 3
    ERROR = 4
    CANCELED = 5

    # Mapping of states to valid previous states
    valid_transitions = {
        QUEUED: [INACTIVE],
        RUNNING: [QUEUED, INACTIVE],
        SUCCESS: [RUNNING],
        ERROR: [QUEUED, RUNNING],
        CANCELED: [INACTIVE, QUEUED, RUNNING]
    }

    @staticmethod
    def isValid(status):
        event = events.trigger('jobs.status.validate', info=status)

        if event.defaultPrevented and len(event.responses):
            return event.responses[-1]

        return status in (JobStatus.INACTIVE, JobStatus.QUEUED,
                          JobStatus.RUNNING, JobStatus.SUCCESS, JobStatus.ERROR,
                          JobStatus.CANCELED)

    @staticmethod
    def toNotificationStatus(status):
        if status in (JobStatus.INACTIVE, JobStatus.QUEUED):
            return ProgressState.QUEUED
        if status == JobStatus.RUNNING:
            return ProgressState.ACTIVE
        if status == JobStatus.SUCCESS:
            return ProgressState.SUCCESS
        else:
            return ProgressState.ERROR

    @staticmethod
    def validTransitions(job, status):
        """
        Returns a list of states that it is valid to transition from for the
        status.

        :param status: The status being transitioned to.
        :type status: str
        :return Returns list of states it valid to transition from.
        """
        event = events.trigger('jobs.status.validTransitions', info={
            'job': job,
            'status': status
        })

        if event.defaultPrevented and len(event.responses):
            return event.responses[-1]

        return JobStatus.valid_transitions.get(status)
