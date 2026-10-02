import io
import json
import os
import subprocess
import time

import pytest
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job
from girder_plugin_worker.constants import PluginSettings as WorkerSettings

from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from pytest_girder.assertions import assertStatus, assertStatusOk
from pytest_girder.utils import getResponseBody

JOB_TERMINAL_STATUSES = {JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED}


@pytest.fixture
def folder(admin):
    f = Folder().createFolder(admin, 'folder', parentType='user')

    yield f


@pytest.fixture
def item(folder, admin):
    f = Item().createItem('item', admin, folder)

    yield f


@pytest.fixture
def file(folder, admin, fsAssetstore):

    sampleData = b'Hello world'
    f = Upload().uploadFromFile(
        obj=io.BytesIO(sampleData), size=len(sampleData), name='Sample',
        parentType='folder', parent=folder, user=admin)

    yield f


@pytest.fixture
def adminToken(admin):
    yield Token().createToken(admin)


def splitName(name):
    if ':' in name.split('/')[-1]:
        imageAndTag = name.rsplit(':', 1)
    else:
        imageAndTag = name.split('@')
    return imageAndTag[0], imageAndTag[1]


class ImageHelper:
    TIMEOUT = 180

    def __init__(self, server, admin, folder):
        self.server = server
        self.admin = admin
        self.folder = folder

    @staticmethod
    def assertHasKeys(obj, keys):
        for key in keys:
            assert key in obj

    @staticmethod
    def assertNotHasKeys(obj, keys):
        for key in keys:
            assert key not in obj

    def waitForJob(self, job, status):
        """
        Poll a job until it reaches a terminal state.

        The legacy helper waited on the ``jobs.job.update.after`` event and
        bound/unbound named listeners; polling from the database avoids the
        races and listener leaks that came with that approach.
        """
        deadline = time.time() + self.TIMEOUT
        while job['status'] not in JOB_TERMINAL_STATUSES:
            if time.time() > deadline:
                raise AssertionError(
                    'job is taking longer than %d seconds' % self.TIMEOUT)
            time.sleep(0.2)
            job = Job().load(id=job['_id'], force=True, includeLog=True)
        assert job['status'] == status, 'The status of the job should match'
        return job

    def getEndpoint(self):
        resp = self.server.request(path='/slicer_cli_web/docker_image',
                                   user=self.admin)
        assertStatus(resp, 200)

        return json.loads(getResponseBody(resp))

    def assertNoImages(self):
        data = self.getEndpoint()
        assert {} == data, 'There should be no pre existing docker images'

    def imageIsLoaded(self, name, exists):
        userAndRepo, tag = splitName(name)

        data = self.getEndpoint()
        if not exists:
            if userAndRepo in data:
                imgVersions = data[userAndRepo]
                self.assertNotHasKeys(imgVersions, [tag])
        else:
            self.assertHasKeys(data, [userAndRepo])
            imgVersions = data[userAndRepo]
            self.assertHasKeys(imgVersions, [tag])

    def endpointsExist(self, name, present=None, absent=None):
        """
        Test if endpoints for particular image exist.

        :param name: name of the image used to determine endpoint location.
        :param present: a list of endpoints within the image that must exist.
        :param absent: a list of endpoints that should be in the image but not
            have endpoints.
        """
        present = present or []
        absent = absent or []
        userAndRepo, tag = splitName(name)
        data = self.getEndpoint()
        for cli in present:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertHasKeys(data[userAndRepo][tag], [cli])
            path = data[userAndRepo][tag][cli]['xmlspec']
            resp = self.server.request(path=path, user=self.admin, isJson=False)
            assertStatusOk(resp)
        for cli in absent:
            self.assertHasKeys(data, [userAndRepo])
            self.assertHasKeys(data[userAndRepo], [tag])
            self.assertNotHasKeys(data[userAndRepo][tag], [cli])

    def deleteImage(self, name, responseCodeOK, deleteDockerImage=False,
                    status=JobStatus.ERROR):
        """
        Delete docker image metadata and (optionally) the local docker image.

        Removing the image from the local docker repository is currently a
        no-op in the server (see ``DockerResource._deleteDockerImages``), so
        unlike the legacy helper there is no background job to wait on.  The
        ``deleteDockerImage`` and ``status`` arguments are kept so the callers
        remain readable.
        """
        resp = self.server.request(
            path='/slicer_cli_web/docker_image', user=self.admin,
            method='DELETE', params={
                'name': json.dumps(name),
                'delete_from_local_repo': deleteDockerImage,
            }, isJson=False)
        if responseCodeOK:
            assertStatus(resp, 200)
        else:
            assertStatus(resp, 400)

    def addImage(self, name, status, initialStatus=200):
        """
        Test the put endpoint.

        :param name: a string or a list of strings
        :param status: either JobStatus.SUCCESS or JobStatus.ERROR.
        :param initialStatus: 200 if the job should run, otherwise a HTTP error
            code expected if the job will fail.
        """
        resp = self.server.request(
            path='/slicer_cli_web/docker_image',
            user=self.admin, method='PUT', params={
                'name': json.dumps(name), 'folder': self.folder['_id']},
            isJson=initialStatus == 200)

        assertStatus(resp, initialStatus)
        if initialStatus != 200:
            return
        # We should have a job ID
        assert resp.json.get('_id') is not None

        job = Job().load(id=resp.json['_id'], force=True, includeLog=True)
        self.waitForJob(job, status)


@pytest.fixture
def fileset(db, admin, fsAssetstore):
    f1 = Folder().createFolder(admin, 'folder1', parentType='user')
    f2 = Folder().createFolder(admin, 'folder2', parentType='user')
    results = {
        'folder1': f1,
        'folder2': f2,
        'item1': [],
        'item2': [],
        'file1': [],
        'file2': [],
    }
    for fidx, folder in enumerate([f1, f2]):
        for idx in range(10):
            sampleData = b'Sample %d' % idx
            f = Upload().uploadFromFile(
                obj=io.BytesIO(sampleData), size=len(sampleData),
                name='Sample %d' % idx, parentType='folder', parent=folder,
                user=admin)
            results['file%d' % (fidx + 1)].append(f)
            i = Item().load(f['itemId'], force=True)
            if not (idx % 2):
                i['largeImage'] = {'fileId': str(f['_id'])}
                i = Item().save(i)
            results['item%d' % (fidx + 1)].append(i)
    yield results


@pytest.fixture
def girderWorker(db):
    """
    Run an instance of Girder worker, connected to rabbitmq.  The rabbitmq
    service must be running.
    """
    broker = 'amqp://guest@127.0.0.1'
    backend = 'rpc://guest@127.0.0.1'

    env = os.environ.copy()
    env['C_FORCE_ROOT'] = 'true'
    env['GIRDER_WORKER_BROKER'] = broker
    env['GIRDER_WORKER_BACKEND'] = backend
    proc = subprocess.Popen([
        'celery', '-A', 'girder_worker.app', '--broker', broker,
        '--result-backend', backend, 'worker', '--concurrency=1'],
        close_fds=True, env=env)
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture
def smallDocker(boundServer, girderWorker, admin, folder):
    Setting().set(WorkerSettings.API_URL, f'http://localhost:{boundServer.boundPort}/api/v1')

    resp = boundServer.request(
        path='/slicer_cli_web/docker_image', user=admin, method='PUT',
        params={
            'name': json.dumps(['girder/slicer_cli_web:small']),
            'folder': folder['_id']
        })
    job = Job().load(id=resp.json['_id'], force=True)
    while job['status'] not in {JobStatus.SUCCESS, JobStatus.CANCELED, JobStatus.ERROR}:
        time.sleep(0.2)
        job = Job().load(id=job['_id'], force=True)
    yield {
        'Example1': Item().findOne({'name': 'Example1'}),
        'Example2': Item().findOne({'name': 'Example2'}),
        'Example3': Item().findOne({'name': 'Example3'}),
    }
    boundServer.request(
        path='/slicer_cli_web/docker_image', user=admin, method='DELETE',
        params={
            'name': json.dumps(['girder/slicer_cli_web:small']),
            'delete_from_local_repo': False,
        })
    Setting().unset(WorkerSettings.API_URL)


@pytest.fixture
def images(boundServer, girderWorker, admin, folder):
    """
    Helper for exercising the docker image ingestion endpoints.

    Uses a bound server (rather than the embedded one) because the ingestion
    job runs on a real worker that has to call back into the Girder API.
    """
    Setting().set(WorkerSettings.API_URL, f'http://localhost:{boundServer.boundPort}/api/v1')
    yield ImageHelper(boundServer, admin, folder)
    Setting().unset(WorkerSettings.API_URL)
