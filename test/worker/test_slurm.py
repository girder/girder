import os
import textwrap
import time
from unittest import mock

import pytest
from girder_worker.slurm.girder_worker_slurm import (SLURM_POLL_INTERVAL, SlurmThread,
                                                     _generate_apptainer_command, _get_slurm_config,
                                                     _process_container_args,
                                                     _slurm_apptainer_config, get_slurm_job_status)


def _run_until_exit_condition(exit_condition, readers, writers):
    """
    Deterministic stand-in for select_loop

    Waits for the exit condition, so monitor-thread errors are visible to
    slurm_dispatch.
    """
    while not exit_condition():
        time.sleep(0.01)


VOLUMES = {
    '/tmp/girder_worker/tempvolume': {'bind': '/container/tmp', 'mode': 'rw'},
    '/data/assetstore': {'bind': '/container/assetstore', 'mode': 'rw'},
}


def test_get_slurm_config_extracts_slurm_args():
    container_args = ['task', '--slurm_partition', 'girdercompute', '--slurm_mem', '4G']
    assert _get_slurm_config(container_args) == [
        '--partition=girdercompute',
        '--mem=4G',
    ]


def test_get_slurm_config_ignores_non_slurm_args():
    assert _get_slurm_config(['task', '--flag', 'value']) == []


def test_get_slurm_config_partition_env_override(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_SLURM_PARTITION', 'debug')
    assert _get_slurm_config(['task']) == ['--partition=debug']
    # An explicit --slurm_partition argument takes precedence
    assert _get_slurm_config(['task', '--slurm_partition', 'girdercompute']) == [
        '--partition=girdercompute'
    ]


def test_process_container_args_filters_slurm_args():
    container_args = [
        'task',
        '/container/assetstore/image.tiff',
        '--slurm_partition',
        'girdercompute',
    ]
    filtered = _process_container_args(container_args, {'volumes': VOLUMES})
    assert '--slurm_partition' not in filtered
    assert 'girdercompute' not in filtered
    # Paths matching a volume bind are replaced by the volume key
    assert filtered == ['task', '/data/assetstore/image.tiff']


def test_process_container_args_mount_prefix_set(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX', '/mnt/slurm')
    container_args = [
        '/container/assetstore/image.tiff',
        '/container/tmp/output.txt',
    ]
    # The mount prefix is only applied to assetstore-like volume keys
    assert _process_container_args(container_args, {'volumes': VOLUMES}) == [
        '/mnt/slurm/data/assetstore/image.tiff',
        '/tmp/girder_worker/tempvolume/output.txt',
    ]


def test_process_container_args_mount_prefix_unset(monkeypatch):
    # Regression test: an unset GIRDER_WORKER_SLURM_MOUNT_PREFIX used to raise
    # a TypeError (None + str) when mapping assetstore volume keys.
    monkeypatch.delenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX', raising=False)
    container_args = ['/container/assetstore/image.tiff']
    assert _process_container_args(container_args, {'volumes': VOLUMES}) == [
        '/data/assetstore/image.tiff'
    ]


def test_generate_apptainer_command(monkeypatch):
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')
    cmd = _generate_apptainer_command(
        ['task', '--flag'],
        {
            'image': 'dsarchive_histomicstk_latest.sif',
            'pwd': '/container/tmp',
            'volumes': VOLUMES,
            'entrypoint': './docker-entrypoint.sh',
        },
    )
    assert cmd == [
        '--pwd', '/container/tmp',
        '--bind',
        '/tmp/girder_worker/tempvolume,/data/assetstore',
        '/sif/dsarchive_histomicstk_latest.sif',
        './docker-entrypoint.sh',
        'task', '--flag',
    ]


def test_generate_apptainer_command_requires_pwd():
    with pytest.raises(Exception, match='PWD cannot be empty'):
        _generate_apptainer_command([], {'image': 'image.sif', 'pwd': '', 'volumes': {}})


def test_generate_apptainer_command_requires_image():
    with pytest.raises(Exception, match='Plugin Not available'):
        _generate_apptainer_command([], {'image': None, 'pwd': '/tmp', 'volumes': {}})


def test_generate_apptainer_command_sif_path_without_env(monkeypatch):
    monkeypatch.delenv('SIF_IMAGE_PATH', raising=False)
    cmd = _generate_apptainer_command([], {'image': 'image.sif', 'pwd': '/tmp', 'volumes': {}})
    assert 'image.sif' in cmd


def test_slurm_apptainer_config(monkeypatch):
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')
    monkeypatch.setenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX', '/mnt/slurm')
    command, slurm_config = _slurm_apptainer_config(
        ['task', '--slurm_ntasks', '2'],
        image='image.sif',
        pwd='/container/tmp',
        volumes=VOLUMES,
        entrypoint='./docker-entrypoint.sh',
    )
    assert slurm_config == ['--ntasks=2']
    assert command == [
        '--pwd', '/container/tmp',
        '--bind',
        '/tmp/girder_worker/tempvolume,/data/assetstore',
        '/sif/image.sif',
        './docker-entrypoint.sh',
        'task',
    ]


def test_get_slurm_job_status_parses_job_state():
    def fake_run(cmd, capture_output):
        return mock.Mock(returncode=0, stdout=b'JobState=RUNNING NumJobs=1\n')

    with mock.patch('subprocess.run', fake_run):
        assert get_slurm_job_status('42') == 'RUNNING'


def test_get_slurm_job_status_invalid_on_error():
    def fake_run(cmd, capture_output):
        return mock.Mock(returncode=1, stdout=b'')

    with mock.patch('subprocess.run', fake_run):
        assert get_slurm_job_status('42') == 'INVALID'


def test_submit_script_is_packaged():
    from girder_worker.slurm import girder_worker_slurm

    template = os.path.join(os.path.dirname(girder_worker_slurm.__file__), 'singularity.slurm')
    with open(template) as f:
        content = f.read()
    assert textwrap.dedent(content).startswith('#!/bin/bash')
    assert '#SBATCH --partition=girdercompute' in content
    assert 'apptainer exec "$@"' in content


def test_slurm_dispatch_raises_on_submit_failure(monkeypatch, tmp_path):
    """A submission failure must fail the girder job, not just be logged."""
    from girder_worker.slurm.girder_worker_slurm import slurm_dispatch

    submit_script = tmp_path / 'submit.sh'
    submit_script.write_text('#!/bin/bash\napptainer exec "$@"\n')
    monkeypatch.setenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', str(submit_script))
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')

    task = mock.Mock()
    task.canceled = False

    with mock.patch(
        'girder_worker.slurm.girder_worker_slurm.utils.select_loop',
        _run_until_exit_condition,
    ):
        with mock.patch('subprocess.run', return_value=mock.Mock(
                returncode=1, stdout=b'', stderr=b'sbatch: error')):
            with pytest.raises(Exception, match='Failed to submit job'):
                slurm_dispatch(
                    task,
                    ['task'],
                    {
                        'image': 'image.sif',
                        'pwd': '/container/tmp',
                        'volumes': VOLUMES,
                        'entrypoint': './docker-entrypoint.sh',
                    },
                    [],
                    [],
                    str(tmp_path / 'log.txt'),
                )


def test_slurm_dispatch_raises_when_job_fails(monkeypatch, tmp_path):
    from girder_worker.slurm.girder_worker_slurm import slurm_dispatch

    submit_script = tmp_path / 'submit.sh'
    submit_script.write_text('#!/bin/bash\napptainer exec "$@"\n')
    monkeypatch.setenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', str(submit_script))
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')

    log_file = tmp_path / 'log.txt'
    log_file.write_text('')

    task = mock.Mock()
    task.canceled = False

    def thread_run(self):
        self.job_id = '42'
        self.error = Exception('Slurm job 42 exited as FAILED')

    monkeypatch.setattr(SlurmThread, 'run', thread_run)

    with mock.patch(
        'girder_worker.slurm.girder_worker_slurm.utils.select_loop',
        _run_until_exit_condition,
    ):
        with pytest.raises(Exception, match='exited as FAILED'):
            slurm_dispatch(
                task,
                ['task'],
                {
                    'image': 'image.sif',
                    'pwd': '/container/tmp',
                    'volumes': VOLUMES,
                    'entrypoint': './docker-entrypoint.sh',
                },
                [],
                [],
                str(log_file),
            )


def test_slurm_dispatch_requires_submit_script(monkeypatch, tmp_path):
    from girder_worker.slurm.girder_worker_slurm import slurm_dispatch

    monkeypatch.delenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', raising=False)
    task = mock.Mock()
    with pytest.raises(Exception, match='GIRDER_WORKER_SLURM_SUBMIT_SCRIPT'):
        slurm_dispatch(
            task,
            ['task'],
            {
                'image': 'image.sif',
                'pwd': '/container/tmp',
                'volumes': VOLUMES,
                'entrypoint': './docker-entrypoint.sh',
            },
            [],
            [],
            str(tmp_path / 'log.txt'),
        )


def test_poll_interval_is_sane():
    assert 0 < SLURM_POLL_INTERVAL <= 60
