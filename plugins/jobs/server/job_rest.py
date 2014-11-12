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
from girder.api.describe import Description
from girder.api.rest import Resource, loadmodel
from girder.constants import AccessType


class Job(Resource):
    def __init__(self):
        self.resourceName = 'job'

        self.route('GET', (':id',), self.getJob)
        self.route('PUT', (':id',), self.updateJob)

    @access.public
    @loadmodel(map={'id': 'job'}, model='job', plugin='jobs',
               level=AccessType.READ)
    def getJob(self, job, params):
        return self.model('job', 'jobs').filter(job, self.getCurrentUser())
    getJob.description = (
        Description('Get a job by ID.')
        .param('id', 'The ID of the job.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the job.', 403))

    @access.token
    @loadmodel(map={'id': 'job'}, model='job', plugin='jobs', force=True)
    def updateJob(self, job, params):
        user = self.getCurrentUser()
        if user is None:
            self.ensureTokenScopes('jobs.write_' + job['_id'])
        else:
            self.model('job').requireAccess(job, user, level=AccessType.WRITE)

        # TODO actually modify the job based on the params

        return job
    updateJob.description = (
        Description('Update an existing job.')
        .notes('In most cases, regular users should not call this endpoint. It '
               'will typically be used by a batch processing system to send '
               'updates regarding the execution of the job. If using a non-'
               'user-associated token for authorization, the token must be '
               'granted the "jobs.write_<id>" scope, where <id> is the ID of '
               'the job being updated.')
        .param('id', 'The ID of the job.')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the job.', 403))
