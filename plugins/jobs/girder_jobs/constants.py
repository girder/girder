# -*- coding: utf-8 -*-
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
