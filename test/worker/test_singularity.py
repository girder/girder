import os
from unittest import mock

import pytest
from girder_worker.singularity.girder_worker_singularity import (GIRDER_WORKER_SINGULARITY_ENV,
                                                                 SingularityPlugin,
                                                                 singularity_enabled)
from girder_worker.singularity.girder_worker_singularity.tasks import (_apptainer_exec_command,
                                                                       _bind_specs,
                                                                       _resolve_image_path)


@pytest.mark.parametrize('value,expected', [
    (None, False),
    ('', False),
    ('0', False),
    ('false', False),
    ('no', False),
    ('1', True),
    ('true', True),
    ('YES', True),
])
def test_singularity_enabled_flag(value, expected, monkeypatch):
    if value is None:
        monkeypatch.delenv(GIRDER_WORKER_SINGULARITY_ENV, raising=False)
    else:
        monkeypatch.setenv(GIRDER_WORKER_SINGULARITY_ENV, value)
    assert singularity_enabled() is expected


def test_task_imports_gated_by_flag(monkeypatch):
    plugin = SingularityPlugin(app=None)

    monkeypatch.delenv(GIRDER_WORKER_SINGULARITY_ENV, raising=False)
    assert plugin.task_imports() == []

    monkeypatch.setenv(GIRDER_WORKER_SINGULARITY_ENV, '1')
    assert plugin.task_imports() == [
        'girder_worker.singularity.girder_worker_singularity.tasks'
    ]


def test_resolve_image_path(monkeypatch):
    monkeypatch.delenv('SIF_IMAGE_PATH', raising=False)
    assert _resolve_image_path('/absolute/path/image.sif') == '/absolute/path/image.sif'
    assert _resolve_image_path('image.sif') == 'image.sif'

    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')
    assert _resolve_image_path('image.sif') == '/sif/image.sif'
    assert _resolve_image_path('/absolute/path/image.sif') == '/absolute/path/image.sif'


def test_bind_specs_deduplicates_host_and_container_paths():
    volumes = {
        '/tmp/host1': {'bind': '/container1', 'mode': 'rw'},
        '/tmp/host2': {'bind': '/container2', 'mode': 'ro'},
    }
    # host and container bind paths are both bound (when they differ)
    assert set(_bind_specs(volumes)) == {
        '/tmp/host1:/tmp/host1:rw',
        '/tmp/host1:/container1:rw',
        '/tmp/host2:/tmp/host2:ro',
        '/tmp/host2:/container2:ro',
    }
    assert _bind_specs(None) == []


def test_apptainer_exec_command():
    cmd = _apptainer_exec_command(
        'image.sif',
        ['task', '--flag'],
        pwd='/work',
        volumes={'/tmp/host': {'bind': '/container', 'mode': 'rw'}},
        entrypoint='./docker-entrypoint.sh',
    )
    assert cmd == [
        'apptainer', 'exec',
        '--pwd', '/work',
        '--bind', '/tmp/host:/tmp/host:rw,/tmp/host:/container:rw',
        'image.sif',
        './docker-entrypoint.sh',
        'task', '--flag',
    ]


def test_apptainer_exec_command_nvidia():
    cmd = _apptainer_exec_command('image.sif', [], nvidia=True)
    assert cmd == ['apptainer', 'exec', '--nv', 'image.sif']


def test_slurm_not_configured_without_submit_script(monkeypatch):
    from girder_worker.singularity.girder_worker_singularity.tasks import slurm_configured

    monkeypatch.delenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', raising=False)
    assert slurm_configured() is False

    monkeypatch.setenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', '/path/to/submit.sh')
    assert slurm_configured() is True


def test_singularity_run_requires_log_file():
    from girder_worker.singularity.girder_worker_singularity.tasks import singularity_run

    task = mock.Mock()
    with pytest.raises(Exception, match='log_file'):
        singularity_run(task, image='image.sif', log_file=None)


def test_singularity_run_requires_image():
    from girder_worker.singularity.girder_worker_singularity.tasks import singularity_run

    task = mock.Mock()
    with pytest.raises(Exception, match='Image name cannot be empty'):
        singularity_run(task, image=None, log_file='log.txt', volumes={},
                        container_args=[], stream_connectors=[])


def test_singularity_run_direct_apptainer_invocation(monkeypatch, tmp_path):
    """With no slurm configured, singularity_run must invoke apptainer directly."""
    from girder_worker.singularity.girder_worker_singularity import tasks

    monkeypatch.delenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT', raising=False)
    log_file = tmp_path / 'log.txt'

    task = mock.Mock()
    task.canceled = False
    task.request = mock.Mock(girder_result_hooks=[mock.sentinel.hook])

    popen = mock.Mock()
    popen.poll.return_value = 0
    popen.wait.return_value = 0
    popen.stdout = mock.Mock()
    commands = []

    def fake_popen(cmd, **kwargs):
        commands.append(cmd)
        return popen

    monkeypatch.setattr(tasks.subprocess, 'Popen', fake_popen)
    monkeypatch.setattr(
        tasks.utils, 'select_loop',
        lambda exit_condition, readers, writers: readers.clear() or writers.clear())

    results = tasks.singularity_run(
        task,
        image='image.sif',
        container_args=['task'],
        volumes={'/tmp/host': {'bind': '/container', 'mode': 'rw'}},
        log_file=str(log_file),
        stream_connectors=[],
    )

    assert commands == [[
        'apptainer', 'exec',
        '--bind', '/tmp/host:/tmp/host:rw,/tmp/host:/container:rw',
        'image.sif',
        './docker-entrypoint.sh',
        'task',
    ]]
    # results is a tuple of None values, one per girder_result_hook
    assert results == (None,)
    assert os.path.exists(log_file)
