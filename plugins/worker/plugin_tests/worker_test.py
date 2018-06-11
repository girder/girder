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
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder.models.user import User
from tests import base

from girder_plugin_jobs.models.job import Job
from girder_plugin_jobs.constants import JobStatus
from girder_plugin_worker import celery
from girder_plugin_worker.constants import PluginSettings
from girder_plugin_worker import utils
from girder_plugin_worker.status import CustomJobStatus


def setUpModule():
    base.enabledPlugins.append('worker')
    base.startServer()


def tearDownModule():
    base.stopServer()
    celery._celeryapp = None


def local_job(job):

    Job().updateJob(job, log='job running', status=JobStatus.RUNNING)
    Job().updateJob(job, log='job ran', status=JobStatus.SUCCESS)


class FakeAsyncResult(object):
    def __init__(self):
        self.task_id = 'fake_id'


class WorkerTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.users = [User().createUser(
            'usr' + str(n), 'passwd', 'tst', 'usr', 'u%d@u.com' % n)
            for n in range(2)]
        self.admin = self.users[0]

        self.adminFolder = six.next(Folder().childFolders(
            parent=self.admin, parentType='user', user=self.admin))
        self.adminToken = Token().createToken(self.admin)
        sampleData = b'Hello world'
        self.sampleFile = Upload().uploadFromFile(
            obj=six.BytesIO(sampleData), size=len(sampleData), name='Sample',
            parentType='folder', parent=self.adminFolder, user=self.admin)

    def testWorker(self):
        # Test the settings
        resp = self.request('/system/setting', method='PUT', params={
            'list': json.dumps([{
                'key': PluginSettings.BROKER,
                'value': 'amqp://guest@broker.com'
            }, {
                'key': PluginSettings.BACKEND,
                'value': 'amqp://guest@backend.com'
            }])
        }, user=self.admin)
        self.assertStatusOk(resp)

        # Create a job to be handled by the worker plugin
        jobModel = Job()
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

            self.assertTrue('headers' in sendTaskCalls[0][2])
            self.assertTrue('jobInfoSpec' in sendTaskCalls[0][2]['headers'])

            # Make sure we got and saved the celery task id
            job = jobModel.load(job['_id'], force=True)
            self.assertEqual(job['celeryTaskId'], 'fake_id')
            self.assertEqual(job['status'], JobStatus.QUEUED)

    def testWorkerDifferentTask(self):
        # Test the settings
        resp = self.request('/system/setting', method='PUT', params={
            'key': PluginSettings.API_URL,
            'value': 'bad value'
        }, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'API URL must start with http:// or https://.')

        resp = self.request('/system/setting', method='PUT', params={
            'list': json.dumps([{
                'key': PluginSettings.BROKER,
                'value': 'amqp://guest@broker.com'
            }, {
                'key': PluginSettings.BACKEND,
                'value': 'amqp://guest@backend.com'
            }])
        }, user=self.admin)
        self.assertStatusOk(resp)

        # Create a job to be handled by the worker plugin
        jobModel = Job()
        job = jobModel.createJob(
            title='title', type='foo', handler='worker_handler',
            user=self.admin, public=False, args=(), kwargs={},
            otherFields={
                'celeryTaskName': 'some_other.task',
                'celeryQueue': 'my_other_q'
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
        app = celery.getCeleryApp()
        with mock.patch.object(app, 'send_task') as sendTask:
            sendTask.return_value = FakeAsyncResult()

            jobModel.scheduleJob(job)

            sendTaskCalls = sendTask.mock_calls
            self.assertEqual(len(sendTaskCalls), 1)
            self.assertEqual(sendTaskCalls[0][1], (
                'some_other.task', job['args'], job['kwargs']))
            self.assertIn('queue', sendTaskCalls[0][2])
            self.assertEqual(sendTaskCalls[0][2]['queue'], 'my_other_q')

    def testWorkerCancel(self):
        jobModel = Job()
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
        with mock.patch('celery.Celery') as celeryMock, \
                mock.patch('girder_plugin_worker.event_handlers.AsyncResult') as asyncResult:
            instance = celeryMock.return_value
            instance.send_task.return_value = FakeAsyncResult()

            jobModel.scheduleJob(job)
            jobModel.cancelJob(job)

            asyncResult.assert_called_with('fake_id', app=mock.ANY)
            # Check we called revoke
            asyncResult.return_value.revoke.assert_called_once()
            job = jobModel.load(job['_id'], force=True)
            self.assertEqual(job['status'], CustomJobStatus.CANCELING)

    def testWorkerWithParent(self):
        jobModel = Job()
        parentJob = jobModel.createJob(
            title='title', type='foo', handler='worker_handler',
            user=self.admin, public=False, otherFields={'celeryTaskId': '1234'})
        childJob = jobModel.createJob(
            title='title', type='foo', handler='worker_handler',
            user=self.admin, public=False, otherFields={'celeryTaskId': '5678',
                                                        'celeryParentTaskId': '1234'})

        self.assertEqual(parentJob['_id'], childJob['parentId'])

    def testLocalJob(self):
        # Make sure local jobs still work
        job = Job().createLocalJob(
            title='local', type='local', user=self.users[0],
            module='plugin_tests.worker_test', function='local_job')

        Job().scheduleJob(job)

        job = Job().load(job['_id'], force=True, includeLog=True)
        self.assertIn('job ran', job['log'])

    def testGirderInputSpec(self):
        # Set an API_URL so we can use the spec outside of a rest request
        Setting().set(PluginSettings.API_URL, 'http://127.0.0.1')
        Setting().set(PluginSettings.DIRECT_PATH, True)

        spec = utils.girderInputSpec(self.adminFolder, resourceType='folder')
        self.assertEqual(spec['id'], str(self.adminFolder['_id']))
        self.assertEqual(spec['resource_type'], 'folder')
        self.assertFalse(spec['fetch_parent'])
        self.assertNotIn('direct_path', spec)

        spec = utils.girderInputSpec(self.sampleFile, resourceType='file')
        self.assertEqual(spec['id'], str(self.sampleFile['_id']))
        self.assertEqual(spec['resource_type'], 'file')
        self.assertFalse(spec['fetch_parent'])
        self.assertIn('direct_path', spec)

        Setting().set(PluginSettings.DIRECT_PATH, False)
        spec = utils.girderInputSpec(self.sampleFile, resourceType='file')
        self.assertFalse(spec['fetch_parent'])
        self.assertNotIn('direct_path', spec)

        Setting().set(PluginSettings.DIRECT_PATH, True)
        spec = utils.girderInputSpec(self.sampleFile, resourceType='file', fetchParent=True)
        self.assertTrue(spec['fetch_parent'])
        self.assertNotIn('direct_path', spec)

    def testDirectPathSettingValidation(self):
        # Test the setting
        resp = self.request('/system/setting', method='PUT', params={
            'key': PluginSettings.DIRECT_PATH,
            'value': 'bad value'
        }, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'The direct path setting must be true or false.')
        resp = self.request('/system/setting', method='PUT', params={
            'key': PluginSettings.DIRECT_PATH,
            'value': 'false'
        }, user=self.admin)
        self.assertStatusOk(resp)

    def testWorkerStatusEndpoint(self):
        # Create a job to be handled by the worker plugin
        job = Job().createJob(
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
        job = Job().save(job)
        self.assertEqual(job['status'], JobStatus.INACTIVE)

        # Schedule the job
        with mock.patch('celery.Celery') as celeryMock:
            instance = celeryMock.return_value
            instance.send_task.return_value = FakeAsyncResult()

            Job().scheduleJob(job)

        # Call the worker status endpoint
        resp = self.request('/worker/status', method='GET', user=self.admin)
        self.assertStatusOk(resp)
        self.assertHasKeys(resp.json, ['report', 'stats', 'ping', 'active', 'reserved'])
