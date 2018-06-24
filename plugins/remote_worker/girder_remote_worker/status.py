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

from girder_jobs.constants import JobStatus


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
    # we are running girder_worker.run as a regular celery task
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
