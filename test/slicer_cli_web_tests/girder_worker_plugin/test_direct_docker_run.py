from os.path import basename

import pytest
from slicer_cli_web.girder_worker_plugin.direct_docker_run import (TEMP_VOLUME_DIRECT_MOUNT_PREFIX,
                                                                   CommaJoinedVolumes,
                                                                   DirectGirderFileIdToVolume, run)


class MockedGirderClient:
    def getFile(self, *args, **kwargs):
        return dict(name='abc')

    def downloadFile(self, file_id, file_path):
        with open(file_path, 'w') as f:
            f.write('dummy')


@pytest.mark.plugin('slicer_cli_web')
def test_direct_docker_run(mocker, server, adminToken, file):
    from girder.models.file import File

    docker_run_mock = mocker.patch(
        'slicer_cli_web.girder_worker_plugin.direct_docker_run._docker_run')
    docker_run_mock.return_value = []

    gc_mock = MockedGirderClient()

    path = File().getLocalFilePath(file)

    run(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], filename=basename(path), direct_file_path=None, gc=gc_mock)])
    docker_run_mock.assert_called_once()
    kwargs = docker_run_mock.call_args[1]
    # image
    assert kwargs['image'] == 'test'
    # container args
    assert len(kwargs['container_args']) == 1
    assert kwargs['container_args'][0].endswith(basename(path))
    # volumes
    assert len(kwargs['volumes']) == 1

    target_path = '%s/%s' % (TEMP_VOLUME_DIRECT_MOUNT_PREFIX, basename(path))

    docker_run_mock.reset_mock()

    run(image='test', container_args=[DirectGirderFileIdToVolume(
        file['_id'], direct_file_path=path, gc=gc_mock)])

    docker_run_mock.assert_called_once()
    kwargs = docker_run_mock.call_args[1]
    # image
    assert kwargs['image'] == 'test'
    # container args
    assert kwargs['container_args'] == [target_path]
    # volumes
    assert len(kwargs['volumes']) == 2


@pytest.mark.plugin('slicer_cli_web')
def test_direct_docker_run_multiple_files(mocker, server, file):
    from girder.models.file import File

    docker_run_mock = mocker.patch(
        'slicer_cli_web.girder_worker_plugin.direct_docker_run._docker_run')
    docker_run_mock.return_value = []

    gc_mock = MockedGirderClient()

    path = File().getLocalFilePath(file)

    run(image='test', container_args=[CommaJoinedVolumes([
        DirectGirderFileIdToVolume(file['_id'], filename='direct.dat',
                                   direct_file_path=path, gc=gc_mock),
        DirectGirderFileIdToVolume(file['_id'], filename='downloaded.dat',
                                   direct_file_path=None, gc=gc_mock),
    ])])

    docker_run_mock.assert_called_once()
    kwargs = docker_run_mock.call_args[1]
    first, second = kwargs['container_args'][0].split(',')
    assert first == '%s/direct.dat' % TEMP_VOLUME_DIRECT_MOUNT_PREFIX
    # the second file has no direct path, so it falls back to a download
    assert second.endswith('/downloaded.dat')
    assert not second.startswith(TEMP_VOLUME_DIRECT_MOUNT_PREFIX)
    # one bind mount and the temporary volume
    assert len(kwargs['volumes']) == 2
