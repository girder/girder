#!/usr/bin/env python

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

import io
import json
from unittest import mock
import pytest

from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder_jobs.models.job import Job
from girder_jobs.constants import JobStatus
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder_worker.girder_plugin.constants import PluginSettings
from girder_worker.girder_plugin import celery, utils
from girder_worker.girder_plugin.status import CustomJobStatus


def tearDownModule():
    celery._celeryapp = None


def local_job(job):

    Job().updateJob(job, log='job running', status=JobStatus.RUNNING)
    Job().updateJob(job, log='job ran', status=JobStatus.SUCCESS)


class FakeAsyncResult:
    def __init__(self):
        self.task_id = 'fake_id'


@pytest.fixture
def models(fsAssetstore, admin, user):
    adminFolder = next(Folder().childFolders(
        parent=admin, parentType='user', user=admin))
    adminToken = Token().createToken(admin)
    sampleData = b'Hello world'
    sampleFile = Upload().uploadFromFile(
        obj=io.BytesIO(sampleData), size=len(sampleData), name='Sample',
        parentType='folder', parent=adminFolder, user=admin)

    return {
        'user': user,
        'admin': admin,
        'adminFolder': adminFolder,
        'adminToken': adminToken,
        'sampleFile': sampleFile
    }


@pytest.mark.plugin('worker')
def testWorker(server, models):
    # Test the settings
    resp = server.request('/system/setting', method='PUT', params={
        'list': json.dumps([{
            'key': PluginSettings.BROKER,
            'value': 'amqp://guest@broker.com'
        }, {
            'key': PluginSettings.BACKEND,
            'value': 'rpc://guest@backend.com'
        }])
    }, user=models['admin'])
    assertStatusOk(resp)

    # Create a job to be handled by the worker plugin
    jobModel = Job()
    job = jobModel.createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, args=(), kwargs={})

    job['kwargs'] = {
        'jobInfo': utils.jobInfoSpec(job),
        'inputs': [
            utils.girderInputSpec(models['adminFolder'], resourceType='folder')
        ],
        'outputs': [
            utils.girderOutputSpec(models['adminFolder'], token=models['adminToken'])
        ]
    }
    job = jobModel.save(job)
    assert job['status'] == JobStatus.INACTIVE

    # Schedule the job, make sure it is sent to celery
    with mock.patch('celery.Celery') as celeryMock:
        instance = celeryMock.return_value
        instance.send_task.return_value = FakeAsyncResult()

        jobModel.scheduleJob(job)

        # Make sure we sent the job to celery
        assert len(celeryMock.mock_calls) == 2
        assert celeryMock.mock_calls[0][1] == ('girder_worker',)
        assert celeryMock.mock_calls[0][2] == {
            'broker': 'amqp://guest@broker.com',
            'backend': 'rpc://guest@backend.com'
        }

        sendTaskCalls = celeryMock.return_value.send_task.mock_calls

        assert len(sendTaskCalls) == 1
        assert sendTaskCalls[0][1] == (
            'girder_worker.run', job['args'], job['kwargs'])

        assert 'headers' in sendTaskCalls[0][2]
        assert 'jobInfoSpec' in sendTaskCalls[0][2]['headers']

        # Make sure we got and saved the celery task id
        job = jobModel.load(job['_id'], force=True)
        assert job['celeryTaskId'] == 'fake_id'
        assert job['status'] == JobStatus.QUEUED


@pytest.mark.plugin('worker')
def testWorkerDifferentTask(server, models):
    # Test the settings
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.API_URL,
        'value': 'bad value'
    }, user=models['admin'])
    assertStatus(resp, 400)
    assert resp.json['message'] == 'API URL must start with http:// or https://.'

    resp = server.request('/system/setting', method='PUT', params={
        'list': json.dumps([{
            'key': PluginSettings.BROKER,
            'value': 'amqp://guest@broker.com'
        }, {
            'key': PluginSettings.BACKEND,
            'value': 'rpc://guest@backend.com'
        }])
    }, user=models['admin'])
    assertStatusOk(resp)

    # Create a job to be handled by the worker plugin
    jobModel = Job()
    job = jobModel.createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, args=(), kwargs={},
        otherFields={
            'celeryTaskName': 'some_other.task',
            'celeryQueue': 'my_other_q'
        })

    job['kwargs'] = {
        'jobInfo': utils.jobInfoSpec(job),
        'inputs': [
            utils.girderInputSpec(models['adminFolder'], resourceType='folder')
        ],
        'outputs': [
            utils.girderOutputSpec(models['adminFolder'], token=models['adminToken'])
        ]
    }
    job = jobModel.save(job)

    # Schedule the job, make sure it is sent to celery
    app = celery.getCeleryApp()
    with mock.patch.object(app, 'send_task') as sendTask:
        sendTask.return_value = FakeAsyncResult()

        jobModel.scheduleJob(job)

        sendTaskCalls = sendTask.mock_calls
        assert len(sendTaskCalls) == 1
        assert sendTaskCalls[0][1] == (
            'some_other.task', job['args'], job['kwargs'])
        assert 'queue' in sendTaskCalls[0][2]
        assert sendTaskCalls[0][2]['queue'] == 'my_other_q'


@pytest.mark.plugin('worker')
def testWorkerCancel(models):
    jobModel = Job()
    job = jobModel.createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, args=(), kwargs={})

    job['kwargs'] = {
        'jobInfo': utils.jobInfoSpec(job),
        'inputs': [
            utils.girderInputSpec(models['adminFolder'], resourceType='folder')
        ],
        'outputs': [
            utils.girderOutputSpec(models['adminFolder'], token=models['adminToken'])
        ]
    }
    job = jobModel.save(job)
    assert job['status'] == JobStatus.INACTIVE

    # Schedule the job, make sure it is sent to celery
    with mock.patch('celery.Celery') as celeryMock, \
            mock.patch('girder_worker.girder_plugin.event_handlers.AsyncResult') as asyncResult:
        instance = celeryMock.return_value
        instance.send_task.return_value = FakeAsyncResult()

        jobModel.scheduleJob(job)
        jobModel.cancelJob(job)

        asyncResult.assert_called_with('fake_id', app=mock.ANY)
        # Check we called revoke
        asyncResult.return_value.revoke.assert_called_once()
        job = jobModel.load(job['_id'], force=True)
        assert job['status'] == CustomJobStatus.CANCELING


@pytest.mark.plugin('worker')
def testWorkerWithParent(models):
    jobModel = Job()
    parentJob = jobModel.createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, otherFields={'celeryTaskId': '1234'})
    childJob = jobModel.createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, otherFields={'celeryTaskId': '5678',
                                                         'celeryParentTaskId': '1234'})

    assert parentJob['_id'] == childJob['parentId']


@pytest.mark.skip('Fix module path')
@pytest.mark.plugin('worker')
def testLocalJob(models):
    # Make sure local jobs still work
    job = Job().createLocalJob(
        title='local', type='local', user=models['admin'],
        module='plugin_tests.worker_test', function='local_job')

    Job().scheduleJob(job)

    job = Job().load(job['_id'], force=True, includeLog=True)
    assert 'job ran' in job['log']


@pytest.mark.plugin('worker')
def testGirderInputSpec(models):
    # Set an API_URL so we can use the spec outside of a rest request
    Setting().set(PluginSettings.API_URL, 'http://127.0.0.1')
    Setting().set(PluginSettings.DIRECT_PATH, True)

    spec = utils.girderInputSpec(models['adminFolder'], resourceType='folder')
    assert spec['id'] == str(models['adminFolder']['_id'])
    assert spec['resource_type'] == 'folder'
    assert not spec['fetch_parent']
    assert 'direct_path' not in spec

    spec = utils.girderInputSpec(models['sampleFile'], resourceType='file')
    assert spec['id'] == str(models['sampleFile']['_id'])
    assert spec['resource_type'] == 'file'
    assert not spec['fetch_parent']
    assert 'direct_path' in spec

    Setting().set(PluginSettings.DIRECT_PATH, False)
    spec = utils.girderInputSpec(models['sampleFile'], resourceType='file')
    assert not spec['fetch_parent']
    assert 'direct_path' not in spec

    Setting().set(PluginSettings.DIRECT_PATH, True)
    spec = utils.girderInputSpec(models['sampleFile'], resourceType='file', fetchParent=True)
    assert spec['fetch_parent']
    assert 'direct_path' not in spec


@pytest.mark.plugin('worker')
def testDirectPathSettingValidation(server, models):
    # Test the setting
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.DIRECT_PATH,
        'value': 'bad value'
    }, user=models['admin'])
    assertStatus(resp, 400)
    assert resp.json['message'] == 'The direct path setting must be true or false.'
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.DIRECT_PATH,
        'value': 'false'
    }, user=models['admin'])
    assertStatusOk(resp)


@pytest.mark.plugin('worker')
def testWorkerStatusEndpoint(server, models):
    # Create a job to be handled by the worker plugin
    job = Job().createJob(
        title='title', type='foo', handler='worker_handler',
        user=models['admin'], public=False, args=(), kwargs={})

    job['kwargs'] = {
        'jobInfo': utils.jobInfoSpec(job),
        'inputs': [
            utils.girderInputSpec(models['adminFolder'], resourceType='folder')
        ],
        'outputs': [
            utils.girderOutputSpec(models['adminFolder'], token=models['adminToken'])
        ]
    }
    job = Job().save(job)
    assert job['status'] == JobStatus.INACTIVE

    # Schedule the job
    with mock.patch('celery.Celery') as celeryMock:
        instance = celeryMock.return_value
        instance.send_task.return_value = FakeAsyncResult()

        Job().scheduleJob(job)

    # Call the worker status endpoint
    resp = server.request('/worker/status', method='GET', user=models['admin'])
    assertStatusOk(resp)
    for key in ['report', 'stats', 'ping', 'active', 'reserved']:
        assert key in resp.json
