import io
import json
import os
import subprocess
import time

import pytest
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.upload import Upload
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job
from girder_plugin_worker.constants import PluginSettings as WorkerSettings


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
