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

import json
import mock
import six
from tests import base

JobStatus = None
utils = None
worker = None


def setUpModule():
    base.enabledPlugins.append('worker')
    base.startServer()

    global JobStatus, utils, worker
    from girder.plugins.jobs.constants import JobStatus
    from girder.plugins import worker
    from girder.plugins.worker import utils


def tearDownModule():
    base.stopServer()


class FakeAsyncResult(object):
    def __init__(self):
        self.task_id = 'fake_id'


class WorkerTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [self.model('user').createUser(
            'usr' + str(n), 'passwd', 'tst', 'usr', 'u%d@u.com' % n)
            for n in range(2)]
        self.admin = self.users[0]

        self.adminFolder = six.next(self.model('folder').childFolders(
            parent=self.admin, parentType='user', user=self.admin))
        self.adminToken = self.model('token').createToken(self.admin)

    def testWorker(self):
        # Test the settings
        resp = self.request('/system/setting', method='PUT', params={
            'list': json.dumps([{
                'key': worker.PluginSettings.BROKER,
                'value': 'amqp://guest@broker.com'
            }, {
                'key': worker.PluginSettings.BACKEND,
                'value': 'amqp://guest@backend.com'
            }])
        }, user=self.admin)
        self.assertStatusOk(resp)

        # Create a job to be handled by the worker plugin
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='title', type='foo', handler='worker_handler',
            user=self.admin, public=False, args=(), kwargs={})

        job['kwargs'] = {
            'jobInfo': utils.jobInfoSpec(job),
            'inputs': [
                utils.girderInputSpec(self.adminFolder, resourceType='folder')
            ],
            'outputs': [
                utils.girderOutputSpec(self.adminFolder, token=self.adminToken)
            ]
        }
        job = jobModel.save(job)
        self.assertEqual(job['status'], JobStatus.INACTIVE)

        # Schedule the job, make sure it is sent to celery
        with mock.patch('celery.Celery') as celeryMock:
            instance = celeryMock.return_value
            instance.send_task.return_value = FakeAsyncResult()

            jobModel.scheduleJob(job)

            # Make sure we sent the job to celery
            self.assertEqual(len(celeryMock.mock_calls), 2)
            self.assertEqual(celeryMock.mock_calls[0][1], ('girder_worker',))
            self.assertEqual(celeryMock.mock_calls[0][2], {
                'broker': 'amqp://guest@broker.com',
                'backend': 'amqp://guest@backend.com'
            })

            sendTaskCalls = celeryMock.return_value.send_task.mock_calls
            self.assertEqual(len(sendTaskCalls), 1)
            self.assertEqual(sendTaskCalls[0][1], (
                'girder_worker.run', job['args'], job['kwargs']))

            # Make sure we got and saved the celery task id
            job = jobModel.load(job['_id'], force=True)
            self.assertEqual(job['celeryTaskId'], 'fake_id')
            self.assertEqual(job['status'], JobStatus.QUEUED)

    def testWorkerDifferentTask(self):
        # Test the settings
        resp = self.request('/system/setting', method='PUT', params={
            'list': json.dumps([{
                'key': worker.PluginSettings.BROKER,
                'value': 'amqp://guest@broker.com'
            }, {
                'key': worker.PluginSettings.BACKEND,
                'value': 'amqp://guest@backend.com'
            }])
        }, user=self.admin)
        self.assertStatusOk(resp)

        # Create a job to be handled by the worker plugin
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='title', type='foo', handler='worker_handler',
            user=self.admin, public=False, args=(), kwargs={},
            otherFields={
                'celeryTaskName': 'some_other.task'
            })

        job['kwargs'] = {
            'jobInfo': utils.jobInfoSpec(job),
            'inputs': [
                utils.girderInputSpec(self.adminFolder, resourceType='folder')
            ],
            'outputs': [
                utils.girderOutputSpec(self.adminFolder, token=self.adminToken)
            ]
        }
        job = jobModel.save(job)

        # Schedule the job, make sure it is sent to celery
        with mock.patch('celery.Celery') as celeryMock:
            instance = celeryMock.return_value
            instance.send_task.return_value = FakeAsyncResult()

            jobModel.scheduleJob(job)

            sendTaskCalls = celeryMock.return_value.send_task.mock_calls
            self.assertEqual(len(sendTaskCalls), 1)
            self.assertEqual(sendTaskCalls[0][1], (
                'some_other.task', job['args'], job['kwargs']))
