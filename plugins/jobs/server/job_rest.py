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

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, filtermodel
from girder.constants import AccessType, SortDir


class Job(Resource):
    def __init__(self):
        super(Job, self).__init__()
        self.resourceName = 'job'

        self.route('GET', (), self.listJobs)
        self.route('GET', ('all',), self.listAllJobs)
        self.route('GET', (':id',), self.getJob)
        self.route('PUT', (':id',), self.updateJob)
        self.route('DELETE', (':id',), self.deleteJob)

    @access.public
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('List jobs for a given user.')
        .param('userId', 'The ID of the user whose jobs will be listed. If '
               'not passed or empty, will use the currently logged in user. If '
               'set to "None", will list all jobs that do not have an owning '
               'user.', required=False)
        .pagingParams(defaultSort='created', defaultSortDir=SortDir.DESCENDING)
    )
    def listJobs(self, userId, limit, offset, sort, params):
        currentUser = self.getCurrentUser()
        if not userId:
            user = currentUser
        elif userId.lower() == 'none':
            user = None
        else:
            user = self.model('user').load(userId, user=currentUser, level=AccessType.READ)

        return list(self.model('job', 'jobs').list(
            user=user, offset=offset, limit=limit, sort=sort, currentUser=currentUser))

    @access.admin
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('List all jobs.')
        .pagingParams(defaultSort='created', defaultSortDir=SortDir.DESCENDING)
    )
    def listAllJobs(self, limit, offset, sort, params):
        currentUser = self.getCurrentUser()
        return list(self.model('job', 'jobs').listAll(
            offset=offset, limit=limit, sort=sort, currentUser=currentUser))

    @access.public
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Get a job by ID.')
        .modelParam('id', 'The ID of the job.', model='job', plugin='jobs', level=AccessType.READ,
                    includeLog=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the job.', 403)
    )
    def getJob(self, job, params):
        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Update an existing job.')
        .notes('In most cases, regular users should not call this endpoint. It '
               'will typically be used by a batch processing system to send '
               'updates regarding the execution of the job. If using a non-'
               'user-associated token for authorization, the token must be '
               'granted the "jobs.job_<id>" scope, where <id> is the ID of '
               'the job being updated.')
        .modelParam('id', 'The ID of the job.', model='job', plugin='jobs', force=True)
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
                  progressMessage, params):
        user = self.getCurrentUser()
        if user:
            self.model('job', 'jobs').requireAccess(job, user, level=AccessType.WRITE)
        else:
            self.ensureTokenScopes('jobs.job_' + str(job['_id']))

        return self.model('job', 'jobs').updateJob(
            job, log=log, status=status, overwrite=overwrite, notify=notify,
            progressCurrent=progressCurrent, progressTotal=progressTotal,
            progressMessage=progressMessage)

    @access.user
    @autoDescribeRoute(
        Description('Delete an existing job.')
        .modelParam('id', 'The ID of the job.', model='job', plugin='jobs', level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the job.', 403)
    )
    def deleteJob(self, job, params):
        self.model('job', 'jobs').remove(job)
