from unittest import mock

import pytest
from girder_worker.app import Task, app
from girder_worker.docker.tasks import docker_run


@mock.patch('girder_worker.task.is_revoked')
def test_canceled_is_latched(is_revoked):
    @app.task(base=Task, bind=True)
    def task(self):
        pass

    # Once the revoked list reports the cancel, a later fetch that times out
    # to an empty list must not un-cancel the task.
    is_revoked.side_effect = [False, True, False]
    task.push_request()
    try:
        assert not task.canceled
        assert task.canceled
        assert task.canceled
    finally:
        task.pop_request()
    assert is_revoked.call_count == 2


@pytest.mark.parametrize('canceled', [True, False])
def test_docker_run_canceled_skips_result_hooks(canceled):
    def select_loop(task, *args):
        # the select loop checks for a cancel while the container runs
        task.canceled

    hook = mock.Mock()
    with mock.patch('girder_worker.task.is_revoked', return_value=canceled), \
            mock.patch('girder_worker.docker.tasks._run_container'), \
            mock.patch('girder_worker.docker.tasks._run_select_loop',
                       side_effect=select_loop):
        docker_run.push_request(girder_result_hooks=[hook])
        try:
            docker_run(image='test', pull_image=False)
        finally:
            docker_run.pop_request()

    # a canceled container never wrote its outputs, so they must not be uploaded
    if canceled:
        hook.transform.assert_not_called()
    else:
        hook.transform.assert_called_once()
    hook.exception.assert_not_called()
