import time

import pytest
import requests
from girder.models.token import Token
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job


def waitForBatchJob(job):
    while job['status'] not in {JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED}:
        time.sleep(0.1)
        job = Job().load(id=job['_id'], force=True, includeLog=True)
    results = {'job': job}
    if job['status'] == JobStatus.SUCCESS:
        log = ''.join(job['log']) if 'log' in job else ''
        subjobIds = [entry.split(',', 1)[0] for entry in log.split('Scheduling job ')[1:]]
        subjobs = None
        subjobs = [Job().load(id=id, force=True, includeLog=True) for id in subjobIds]
        while any(subjob['status'] not in {
                JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED} for subjob in subjobs):
            time.sleep(0.1)
            subjobs = [Job().load(id=id, force=True, includeLog=True) for id in subjobIds]
        results['subjobs'] = subjobs
    return results


def scheduleBatchJob(boundServer, admin, data):
    headers = {
        'Accept': 'application/json',
        'Girder-Token': str(Token().createToken(admin)['_id']),
    }
    req = requests.post(
        'http://127.0.0.1:%d/api/v1/slicer_cli_web/girder_slicer_cli_web_small/Example3/run' %
        boundServer.boundPort, headers=headers, data=data)
    assert req.status_code == 200
    return req


@pytest.mark.usefixtures('girderWorker')
@pytest.mark.plugin('slicer_cli_web')
def testBatchOneParam(boundServer, admin, girderWorker, smallDocker, fileset):
    req = scheduleBatchJob(boundServer, admin, data={
        'file1': '',
        'file1_folder': str(fileset['folder1']['_id']),
        'image1': str(fileset['file1'][0]['_id']),
        'item1': str(fileset['item1'][0]['_id']),
    })
    assert req.status_code == 200
    results = waitForBatchJob(req.json())
    assert results['job']['status'] == JobStatus.SUCCESS
    assert len(results['subjobs']) == len(fileset['file1'])
    assert 'item match' in ''.join(results['subjobs'][0]['log'])
    for subjob in results['subjobs'][1:]:
        assert 'item match' not in ''.join(subjob['log'])


@pytest.mark.usefixtures('girderWorker')
@pytest.mark.plugin('slicer_cli_web')
def testBatchImageParam(boundServer, admin, girderWorker, smallDocker, fileset):
    req = scheduleBatchJob(boundServer, admin, data={
        'file1': str(fileset['file1'][0]['_id']),
        'image1': r'[0-5]',
        'image1_folder': str(fileset['folder1']['_id']),
        'item1': str(fileset['item1'][0]['_id']),
    })
    assert req.status_code == 200
    results = waitForBatchJob(req.json())
    assert results['job']['status'] == JobStatus.SUCCESS
    assert len(results['subjobs']) == 3
    assert 'item match' in ''.join(results['subjobs'][0]['log'])
    for subjob in results['subjobs'][1:]:
        assert 'item match' not in ''.join(subjob['log'])


@pytest.mark.usefixtures('girderWorker')
@pytest.mark.plugin('slicer_cli_web')
def testBatchTwoParams(boundServer, admin, girderWorker, smallDocker, fileset):
    req = scheduleBatchJob(boundServer, admin, data={
        'file1': '',
        'file1_folder': str(fileset['folder1']['_id']),
        'image1': str(fileset['file1'][0]['_id']),
        'item1': '',
        'item1_folder': str(fileset['folder1']['_id']),
    })
    assert req.status_code == 200
    results = waitForBatchJob(req.json())
    assert results['job']['status'] == JobStatus.SUCCESS
    assert len(results['subjobs']) == len(fileset['file1'])
    assert 'item match' in ''.join(results['subjobs'][0]['log'])
    for subjob in results['subjobs'][1:]:
        assert 'item match' not in ''.join(subjob['log'])


@pytest.mark.plugin('slicer_cli_web')
def testBatchMismatchedLists(boundServer, admin, girderWorker, smallDocker, fileset):
    req = scheduleBatchJob(boundServer, admin, data={
        'file1': '[0-3]',
        'file1_folder': str(fileset['folder1']['_id']),
        'image1': '[0-3]',
        'image1_folder': str(fileset['folder1']['_id']),
        'item1': str(fileset['item1'][0]['_id']),
    })
    assert req.status_code == 200
    results = waitForBatchJob(req.json())
    assert results['job']['status'] == JobStatus.ERROR
    assert 'different number of entries on batch inputs' in ''.join(results['job']['log'])


@pytest.mark.usefixtures('girderWorker')
@pytest.mark.plugin('slicer_cli_web')
def testBatchCancel(boundServer, admin, girderWorker, smallDocker, fileset):
    req = scheduleBatchJob(boundServer, admin, data={
        'file1': '',
        'file1_folder': str(fileset['folder1']['_id']),
        'image1': str(fileset['file1'][0]['_id']),
        'item1': str(fileset['item1'][0]['_id']),
    })
    assert req.status_code == 200
    job = Job().load(id=req.json()['_id'], force=True, includeLog=True)
    Job().cancelJob(job)
    results = waitForBatchJob(req.json())
    assert results['job']['status'] == JobStatus.CANCELED
