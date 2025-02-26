import io
import os
from unittest import mock
import pytest

from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder_jobs.models.job import Job
from girder_jobs.constants import JobStatus
from pytest_girder.assertions import assertStatus, assertStatusOk

from girder_plugin_worker.constants import PluginSettings
from girder_plugin_worker import utils
from girder_worker.app import app


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
    os.environ['GIRDER_SETTING_WORKER_API_URL'] = 'http://localhost:8080/api/v1'
    os.environ['GIRDER_WORKER_BROKER'] = 'amqp://guest@broker.com'
    os.environ['GIRDER_WORKER_BACKEND'] = 'rpc://guest@backend.com'

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
    with mock.patch.object(app, 'send_task') as sendTask:
        sendTask.return_value = FakeAsyncResult()

        jobModel.scheduleJob(job)

        # Make sure we sent the job to celery
        sendTaskCalls = sendTask.mock_calls

        assert len(sendTaskCalls) == 1
        assert sendTaskCalls[0][1] == (
            'girder_worker.run', job['args'], job['kwargs'])

        assert 'headers' in sendTaskCalls[0][2]
        assert 'jobInfoSpec' in sendTaskCalls[0][2]['headers']

        # Make sure we got and saved the celery task id
        job = jobModel.load(job['_id'], force=True)
        assert job['celeryTaskId'] == 'fake_id'
        assert job['status'] == JobStatus.QUEUED

    del os.environ['GIRDER_SETTING_WORKER_API_URL']
    del os.environ['GIRDER_WORKER_BROKER']
    del os.environ['GIRDER_WORKER_BACKEND']


@pytest.mark.plugin('worker')
def testWorkerDifferentTask(server, models):
    # Test the settings
    resp = server.request('/system/setting', method='PUT', params={
        'key': PluginSettings.API_URL,
        'value': 'bad value'
    }, user=models['admin'])
    assertStatus(resp, 400)
    assert resp.json['message'] == 'API URL must start with http:// or https://.'

    os.environ['GIRDER_WORKER_BROKER'] = 'amqp://guest@broker.com'
    os.environ['GIRDER_WORKER_BACKEND'] = 'rpc://guest@backend.com'

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
    with mock.patch.object(app, 'send_task') as sendTask:
        sendTask.return_value = FakeAsyncResult()

        jobModel.scheduleJob(job)

        sendTaskCalls = sendTask.mock_calls
        assert len(sendTaskCalls) == 1
        assert sendTaskCalls[0][1] == (
            'some_other.task', job['args'], job['kwargs'])
        assert 'queue' in sendTaskCalls[0][2]
        assert sendTaskCalls[0][2]['queue'] == 'my_other_q'

    del os.environ['GIRDER_WORKER_BROKER']
    del os.environ['GIRDER_WORKER_BACKEND']


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
    Setting().set(PluginSettings.API_URL, 'http://127.0.0.1/api/v1')
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
    # Set an API_URL so we can use the spec outside of a rest request
    Setting().set(PluginSettings.API_URL, 'http://127.0.0.1/api/v1')

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
