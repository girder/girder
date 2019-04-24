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

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir
from girder.models.user import User
from .models.job import Job as JobModel
from . import constants


class Job(Resource):

    def __init__(self):
        super(Job, self).__init__()
        self.resourceName = 'job'
        self._model = JobModel()

        self.route('GET', (), self.listJobs)
        self.route('POST', (), self.createJob)
        self.route('GET', ('all',), self.listAllJobs)
        self.route('GET', (':id',), self.getJob)
        self.route('PUT', (':id',), self.updateJob)
        self.route('PUT', (':id', 'cancel'), self.cancelJob)
        self.route('DELETE', (':id',), self.deleteJob)
        self.route('GET', ('typeandstatus', 'all',), self.allJobsTypesAndStatuses)
        self.route('GET', ('typeandstatus',), self.jobsTypesAndStatuses)

    @access.public
    @filtermodel(model=JobModel)
    @autoDescribeRoute(
        Description('List jobs for a given user.')
        .param('userId', 'The ID of the user whose jobs will be listed. If '
               'not passed or empty, will use the currently logged in user. If '
               'set to "None", will list all jobs that do not have an owning '
               'user.', required=False)
        .modelParam('parentId', 'Id of the parent job.', model=JobModel, level=AccessType.ADMIN,
                    destName='parentJob', paramType='query', required=False)
        .jsonParam('types', 'Filter for type', requireArray=True, required=False)
        .jsonParam('statuses', 'Filter for status', requireArray=True, required=False)
        .pagingParams(defaultSort='created', defaultSortDir=SortDir.DESCENDING)
    )
    def listJobs(self, userId, parentJob, types, statuses, limit, offset, sort):
        currentUser = self.getCurrentUser()
        if not userId:
            user = currentUser
        elif userId.lower() == 'none':
            user = 'none'
        else:
            user = User().load(userId, user=currentUser, level=AccessType.READ)

        parent = None
        if parentJob:
            parent = parentJob

        return list(self._model.list(
            user=user, offset=offset, limit=limit, types=types,
            statuses=statuses, sort=sort, currentUser=currentUser, parentJob=parent))

    @filtermodel(model=JobModel)
    @access.token(scope=constants.REST_CREATE_JOB_TOKEN_SCOPE, required=True)
    @autoDescribeRoute(
        Description('Create a job model')
        .param('title', 'Title of the job.', required=True)
        .param('type', 'Type of the job.', required=True)
        .modelParam('parentId', 'ID of the parent job.', model=JobModel, destName='parentJob',
                    paramType='query', required=False)
        .param('public', 'Whether the job is publicly visible.', required=False,
               dataType='boolean', default=False)
        .param('handler', 'Job handler string.', required=False)
        .jsonParam('args', 'Job arguments', required=False, requireArray=True)
        .jsonParam('kwargs', 'Job keyword arguments', required=False, requireObject=True)
        .jsonParam('otherFields', 'Other fields specific to the job handler',
                   requireObject=True, required=False)
    )
    def createJob(self, title, type, parentJob, public, handler, args, kwargs, otherFields):
        params = {
            'title': title,
            'type': type,
            'public': public,
            'handler': handler,
            'user': self.getCurrentUser(),
            'args': args,
            'kwargs': kwargs,
            'parentJob': parentJob,
            'otherFields': otherFields
        }
        return self._model.createJob(**params)

    @access.admin
    @filtermodel(model=JobModel)
    @autoDescribeRoute(
        Description('List all jobs.')
        .jsonParam('types', 'Filter for type', requireArray=True, required=False)
        .jsonParam('statuses', 'Filter for status', requireArray=True, required=False)
        .pagingParams(defaultSort='created', defaultSortDir=SortDir.DESCENDING)
    )
    def listAllJobs(self, types, statuses, limit, offset, sort):
        currentUser = self.getCurrentUser()
        return list(self._model.list(
            user='all', offset=offset, limit=limit, types=types,
            statuses=statuses, sort=sort, currentUser=currentUser))

    @access.public
    @filtermodel(JobModel)
    @autoDescribeRoute(
        Description('Get a job by ID.')
        .modelParam('id', 'The ID of the job.', model=JobModel, force=True, includeLog=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the job.', 403)
    )
    def getJob(self, job):
        user = self.getCurrentUser()

        # If the job is not public check access
        if not job.get('public', False):
            if user:
                self._model.requireAccess(job, user, level=AccessType.READ)
            else:
                self.ensureTokenScopes('jobs.job_' + str(job['_id']))

        return job

    @access.token
    @filtermodel(JobModel)
    @autoDescribeRoute(
        Description('Update an existing job.')
        .notes('In most cases, regular users should not call this endpoint. It '
               'will typically be used by a batch processing system to send '
               'updates regarding the execution of the job. If using a non-'
               'user-associated token for authorization, the token must be '
               'granted the "jobs.job_<id>" scope, where <id> is the ID of '
               'the job being updated.')
        .modelParam('id', 'The ID of the job.', model=JobModel, force=True)
        .param('log', 'A message to add to the job\'s log field. If you want '
               'to overwrite any existing log content, pass another parameter '
               '"overwrite=true".', required=False)
        .param('overwrite', 'If passing a log parameter, you may set this to '
               '"true" if you wish to overwrite the log field rather than '
               'append to it.', dataType='boolean', required=False, default=False)
        .param('status', 'Update the status of the job. See the JobStatus '
               'enumeration in the constants module in this plugin for the '
               'numerical values of each status.', required=False)
        .param('progressTotal', 'Maximum progress value, set <= 0 to indicate '
               'indeterminate progress for this job.', required=False, dataType='float')
        .param('progressCurrent', 'Current progress value.', required=False, dataType='float')
        .param('progressMessage', 'Current progress message.', required=False)
        .param('notify', 'If this update should trigger a notification, set '
               'this field to true.', dataType='boolean', required=False, default=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the job.', 403)
    )
    def updateJob(self, job, log, overwrite, notify, status, progressTotal, progressCurrent,
                  progressMessage):
        user = self.getCurrentUser()
        if user:
            self._model.requireAccess(job, user, level=AccessType.WRITE)
        else:
            self.ensureTokenScopes('jobs.job_' + str(job['_id']))

        return self._model.updateJob(
            job, log=log, status=status, overwrite=overwrite, notify=notify,
            progressCurrent=progressCurrent, progressTotal=progressTotal,
            progressMessage=progressMessage)

    @access.user
    @autoDescribeRoute(
        Description('Delete an existing job.')
        .modelParam('id', 'The ID of the job.', model=JobModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the job.', 403)
    )
    def deleteJob(self, job):
        self._model.remove(job)

    @access.admin
    @autoDescribeRoute(
        Description('Get types and statuses of all jobs')
        .errorResponse('Admin access was denied for the job.', 403)
    )
    def allJobsTypesAndStatuses(self):
        return self._model.getAllTypesAndStatuses(user='all')

    @access.user
    @autoDescribeRoute(
        Description('Get types and statuses of jobs of current user')
    )
    def jobsTypesAndStatuses(self):
        currentUser = self.getCurrentUser()
        return self._model.getAllTypesAndStatuses(user=currentUser)

    @access.user
    @filtermodel(JobModel)
    @autoDescribeRoute(
        Description('Cancel a job by ID.')
        .modelParam('id', 'The ID of the job.', model=JobModel, level=AccessType.WRITE,
                    includeLog=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the job.', 403))
    def cancelJob(self, job, params):
        return self._model.cancelJob(job)
