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
CustomJobStatus = None


def setUpModule():
    base.enabledPlugins.append('worker')
    base.startServer()

    global JobStatus, utils, worker, CustomJobStatus
    from girder.plugins.jobs.constants import JobStatus
    from girder.plugins import worker
    from girder.plugins.worker import utils, CustomJobStatus


def tearDownModule():
    base.stopServer()


def local_job(job):
    from girder.utility.model_importer import ModelImporter

    ModelImporter.model('job', 'jobs').updateJob(job, log='job running', status=JobStatus.RUNNING)
    ModelImporter.model('job', 'jobs').updateJob(job, log='job ran', status=JobStatus.SUCCESS)


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
        sampleData = b'Hello world'
        self.sampleFile = self.model('upload').uploadFromFile(
            obj=six.BytesIO(sampleData), size=len(sampleData), name='Sample',
            parentType='folder', parent=self.adminFolder, user=self.admin)

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

            self.assertTrue('headers' in sendTaskCalls[0][2])
            self.assertTrue('jobInfoSpec' in sendTaskCalls[0][2]['headers'])

            # Make sure we got and saved the celery task id
            job = jobModel.load(job['_id'], force=True)
            self.assertEqual(job['celeryTaskId'], 'fake_id')
            self.assertEqual(job['status'], JobStatus.QUEUED)

    def testWorkerDifferentTask(self):
        # Test the settings
        resp = self.request('/system/setting', method='PUT', params={
            'key': worker.PluginSettings.API_URL,
            'value': 'bad value'
        }, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'API URL must start with http:// or https://.')

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
        with mock.patch('celery.Celery') as celeryMock:
            instance = celeryMock.return_value
            instance.send_task.return_value = FakeAsyncResult()

            jobModel.scheduleJob(job)

            sendTaskCalls = celeryMock.return_value.send_task.mock_calls
            self.assertEqual(len(sendTaskCalls), 1)
            self.assertEqual(sendTaskCalls[0][1], (
                'some_other.task', job['args'], job['kwargs']))
            self.assertIn('queue', sendTaskCalls[0][2])
            self.assertEqual(sendTaskCalls[0][2]['queue'], 'my_other_q')

    def testWorkerCancel(self):
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
        with mock.patch('celery.Celery') as celeryMock, \
                mock.patch('girder.plugins.worker.AsyncResult') as asyncResult:
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
        jobModel = self.model('job', 'jobs')
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
        job = self.model('job', 'jobs').createLocalJob(
            title='local', type='local', user=self.users[0],
            module='plugin_tests.worker_test', function='local_job')

        self.model('job', 'jobs').scheduleJob(job)

        job = self.model('job', 'jobs').load(job['_id'], force=True,
                                             includeLog=True)
        self.assertIn('job ran', job['log'])

    def testGirderInputSpec(self):
        # Set an API_URL so we can use the spec outside of a rest request
        self.model('setting').set(worker.PluginSettings.API_URL, 'http://127.0.0.1')
        self.model('setting').set(worker.PluginSettings.DIRECT_PATH, True)

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

        self.model('setting').set(worker.PluginSettings.DIRECT_PATH, False)
        spec = utils.girderInputSpec(self.sampleFile, resourceType='file')
        self.assertFalse(spec['fetch_parent'])
        self.assertNotIn('direct_path', spec)

        self.model('setting').set(worker.PluginSettings.DIRECT_PATH, True)
        spec = utils.girderInputSpec(self.sampleFile, resourceType='file', fetchParent=True)
        self.assertTrue(spec['fetch_parent'])
        self.assertNotIn('direct_path', spec)

    def testDirectPathSettingValidation(self):
        # Test the setting
        resp = self.request('/system/setting', method='PUT', params={
            'key': worker.PluginSettings.DIRECT_PATH,
            'value': 'bad value'
        }, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'The direct path setting must be true or false.')
        resp = self.request('/system/setting', method='PUT', params={
            'key': worker.PluginSettings.DIRECT_PATH,
            'value': 'false'
        }, user=self.admin)
        self.assertStatusOk(resp)
