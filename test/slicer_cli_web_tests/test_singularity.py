from unittest import mock

import pytest
from slicer_cli_web.singularity.slicer_cli_web_singularity.commands import SingularityCommands
from slicer_cli_web.singularity.slicer_cli_web_singularity.utils import (
    generate_image_name_for_singularity, is_valid_image_name_format, sanitize_and_return_json)


def test_is_valid_image_name_format():
    assert is_valid_image_name_format('dsarchive/histomicstk:latest') is True
    assert is_valid_image_name_format('') is False
    assert is_valid_image_name_format('no-tag') is False


def test_generate_image_name_for_singularity():
    assert generate_image_name_for_singularity(
        'dsarchive/histomicstk:latest') == 'dsarchive_histomicstk_latest.sif'
    with pytest.raises(Exception, match='Not a valid image name'):
        generate_image_name_for_singularity('no-tag')


def test_singularity_pull_command(monkeypatch):
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')
    cmd = SingularityCommands.singularity_pull('dsarchive/histomicstk:latest')
    assert cmd == [
        'apptainer', 'pull', '--force',
        '/sif/dsarchive_histomicstk_latest.sif',
        'docker://dsarchive/histomicstk:latest',
    ]


def test_singularity_pull_command_without_sif_path(monkeypatch):
    monkeypatch.delenv('SIF_IMAGE_PATH', raising=False)
    cmd = SingularityCommands.singularity_pull('image:tag')
    assert cmd == ['apptainer', 'pull', '--force', 'image_tag.sif', 'docker://image:tag']


def test_singularity_inspect_command():
    cmd = SingularityCommands.singularity_inspect('image:tag')
    assert cmd == [
        'apptainer', 'inspect', '--json', '-l', 'image_tag.sif',
    ]

    cmd = SingularityCommands.singularity_inspect('image:tag', option='-j', json_format=False)
    assert cmd == ['apptainer', 'inspect', '-j', 'image_tag.sif']


def test_singularity_version_command():
    assert SingularityCommands.singularity_version() == ['apptainer', '--version']


def test_sanitize_and_return_json_labels():
    labels = sanitize_and_return_json(
        '{"data": {"attributes": {"labels": {"org.label-schema.build-date": "today"}}}}')
    assert labels == {'org.label-schema.build-date': 'today'}


def test_sanitize_and_return_json_fallback_parse():
    labels = sanitize_and_return_json('key: value\nother: thing\n')
    assert labels == {'key': 'value', 'other': 'thing'}


def test_run_command_raises_on_failure():
    from slicer_cli_web.singularity.slicer_cli_web_singularity.commands import run_command

    with pytest.raises(Exception, match='Error running command'):
        run_command(['false'])


def test_get_work_dir_defaults_to_root(monkeypatch):
    monkeypatch.setenv('SIF_IMAGE_PATH', '/sif')

    def fake_run_command(cmd):
        if cmd[1:3] == ['sif', 'list']:
            return '1 | JSON.Generic | 3 | 40'
        return '{"WorkingDir": "/work"}'

    with mock.patch(
        'slicer_cli_web.singularity.slicer_cli_web_singularity.commands.run_command',
        side_effect=fake_run_command,
    ):
        assert SingularityCommands.get_work_dir('image:tag') == '/work'


def test_delete_and_ingest_docker_flow_unchanged_when_disabled():
    """When the setting is off, image_job must select the docker flow."""
    from slicer_cli_web import image_job

    with mock.patch.object(
        image_job, 'singularity_enabled', return_value=False,
    ):
        assert image_job._use_singularity() is None


def test_ingest_from_docker_uses_singularity_when_enabled():
    from slicer_cli_web import image_job

    singularity_job = mock.Mock()
    singularity_image = mock.Mock()
    with mock.patch.object(
        image_job, 'singularity_enabled', return_value=True,
    ), mock.patch.object(
        image_job, '_ingest_from_singularity', autospec=True,
    ) as ingest, mock.patch.object(
        image_job, '_use_singularity',
        return_value=(singularity_job, singularity_image),
    ):
        image_job.ingest_from_docker.__wrapped__(
            ['image:tag'], 'token', 'folder', True)

        assert ingest.call_count == 1
        args = ingest.call_args[0]
        assert args[0] is singularity_job
        assert args[1] is singularity_image
        assert args[2].name == 'slicer_cli_web.image_job.ingest_from_docker'
        assert args[3:] == (['image:tag'], 'token', 'folder', True)
