import io
import os
import json

from girder_worker.utils import JobStatus
import pytest

FIXTURE_DIR = os.path.join('..', os.path.dirname(__file__), 'fixtures')


def _assert_job_statuses(job):
    assert [ts['status'] for ts in job['timestamps']] == [JobStatus.RUNNING, JobStatus.SUCCESS]


def _assert_job_contents(r, session, test_file, remove_newline=True):
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)

        # Remove escaped chars
        log = ''.join(str(entry) for entry in job['log'])
        # Remove trailing \n added by test script
        if remove_newline:
            log = log[:-1]

        with open(test_file) as fp:
            assert log == fp.read()


@pytest.mark.docker
def test_docker_run(session):
    r = session.post('integration_tests/docker/test_docker_run')
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)
        assert job['log'] == ['hello docker!\n']


@pytest.mark.docker
@pytest.mark.parametrize('url', [
    'integration_tests/docker/test_docker_run_mount_volume',
    'integration_tests/docker/test_docker_run_mount_idiomatic_volume'
])
def test_docker_run_volumes(url, session):
    r = session.post(url, params={
        'fixtureDir': FIXTURE_DIR
    })
    _assert_job_contents(r, session, os.path.join(FIXTURE_DIR, 'read.txt'))


@pytest.mark.docker
def test_docker_run_named_pipe_output(session, all_writable_tmpdir):
    params = {
        'tmpDir': all_writable_tmpdir,
        'message': 'Dydh da'
    }
    r = session.post('integration_tests/docker/test_docker_run_named_pipe_output', params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)
        assert job['log'] == [params['message']]


@pytest.mark.docker
def test_docker_run_girder_file_to_named_pipe(
        session, test_file, test_file_in_girder, all_writable_tmpdir):
    params = {
        'tmpDir': all_writable_tmpdir,
        'fileId': test_file_in_girder['_id']
    }
    r = session.post(
        'integration_tests/docker/test_docker_run_girder_file_to_named_pipe', params=params)
    _assert_job_contents(r, session, test_file)


@pytest.mark.docker
def test_docker_run_file_upload_to_item(session, girder_client, test_item):
    contents = b'Balaenoptera musculus'
    params = {
        'itemId': test_item['_id'],
        'contents': contents
    }
    r = session.post('integration_tests/docker/test_docker_run_file_upload_to_item',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)

    files = list(girder_client.listFile(test_item['_id']))

    assert len(files) == 1

    file_contents = io.BytesIO()
    girder_client.downloadFile(files[0]['_id'], file_contents)
    file_contents.seek(0)

    assert file_contents.read().strip() == contents


@pytest.mark.docker
@pytest.mark.parametrize('url,strip_lf', [
    ('integration_tests/docker/test_docker_run_girder_file_to_named_pipe_on_temp_vol', True),
    ('integration_tests/docker/test_docker_run_girder_file_to_volume', False)
])
def test_docker_run_girder_file(url, strip_lf, session, test_file, test_file_in_girder):
    r = session.post(url, params={
        'fileId': test_file_in_girder['_id']
    })
    _assert_job_contents(r, session, test_file, remove_newline=strip_lf)


def test_docker_run_download_multi_file_item(session, test_multi_file_item):
    r = session.post('integration_tests/docker/test_docker_run_multi_file_item', params={
        'itemId': test_multi_file_item['_id']
    })
    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)
        log = ''.join(str(entry) for entry in job['log']).strip()
        assert set(log.split()) == {'test0.txt', 'test1.txt', 'test2.txt'}


@pytest.mark.docker
def test_docker_run_progress_pipe(session):
    progressions = [
        {'message': 'Are there yet?', 'total': 100.0, 'current': 10.0},
        {'message': 'How about now?', 'total': 100.0, 'current': 20.0},
        {'message': 'Halfway there!', 'total': 100.0, 'current': 50.0},
        {'message': 'We have arrived!', 'total': 100.0, 'current': 100.0}
    ]
    r = session.post('integration_tests/docker/test_docker_run_progress_pipe', params={
        'progressions': json.dumps(progressions)
    })
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)

        progress = job['progress']

        del progress['notificationId']
        assert progress == progressions[-1]


@pytest.mark.docker
def test_docker_run_transfer_encoding_stream(session, girder_client, test_file,
                                             test_file_in_girder, test_item):
    delimiter = b'_please_dont_common_up_randomly_if_you_do_i_will_eat_my_hat!'
    params = {
        'itemId': test_item['_id'],
        'fileId': test_file_in_girder['_id'],
        'delimiter': delimiter
    }
    r = session.post('integration_tests/docker/test_docker_run_transfer_encoding_stream',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)

    files = list(girder_client.listFile(test_item['_id']))

    assert len(files) == 1

    file_contents = io.BytesIO()
    girder_client.downloadFile(files[0]['_id'], file_contents)
    file_contents.seek(0)
    chunks = file_contents.read().split(delimiter)
    chunks = [c for c in chunks if c]

    # We should have at least 4 chunks
    assert len(chunks) >= 4
    contents = b''.join(chunks)
    with open(test_file, 'rb') as fp:
        assert contents == fp.read()


@pytest.mark.docker
def test_docker_run_temporary_volume_root(session):
    r = session.post('integration_tests/docker/test_docker_run_temporary_volume_root', params={
        'prefix': 'prefix'
    })
    assert r.status_code == 200, r.content

    with session.wait_for_success(r.json()['_id']) as job:
        _assert_job_statuses(job)
        assert len(job['log']) == 1


@pytest.mark.docker
def test_docker_run_bad_exit_code(session):
    r = session.post('integration_tests/docker/test_docker_run_raises_exception')
    assert r.status_code == 200, r.content
    with session.wait_for_success(r.json()['_id']) as job:
        log = ''.join(job['log'])
        assert job['status'] == JobStatus.ERROR
        assert 'girder docker exception' in log
        assert 'Non-zero exit code from docker container' in log


@pytest.mark.docker
def test_docker_run_cancel_sigterm(session):
    params = {
        'mode': 'sigterm'
    }
    r = session.post('integration_tests/docker/test_docker_run_cancel',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_canceled(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.CANCELED]


@pytest.mark.docker
def test_docker_run_cancel_sigkill(session):
    params = {
        'mode': 'sigkill'
    }
    r = session.post('integration_tests/docker/test_docker_run_cancel',
                     params=params)
    assert r.status_code == 200, r.content

    with session.wait_for_canceled(r.json()['_id']) as job:
        assert [ts['status'] for ts in job['timestamps']] == \
            [JobStatus.RUNNING, JobStatus.CANCELED]
