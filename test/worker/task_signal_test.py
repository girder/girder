from unittest import mock

import pytest
from girder_worker.app import (girder_before_task_publish, gw_task_failure, gw_task_prerun,
                               gw_task_success)
from girder_worker.utils import BUILTIN_CELERY_TASKS


@pytest.mark.parametrize('name', BUILTIN_CELERY_TASKS)
def test_girder_before_task_publish_hook_with_builtin_tasks_should_noop(name):
    with mock.patch('girder_worker.app.get_context') as gc:
        girder_before_task_publish(sender=name)
        gc.assert_not_called()


@pytest.mark.parametrize('name', BUILTIN_CELERY_TASKS)
def test_gw_task_prerun_with_builtin_tasks_should_noop(name):
    with mock.patch('girder_worker.app._job_manager') as jm:
        task = mock.MagicMock()
        task.name = name
        gw_task_prerun(sender=task)
        jm.assert_not_called()


@pytest.mark.parametrize('name', BUILTIN_CELERY_TASKS)
def test_gw_task_success_with_builtin_tasks_should_noop(name):
    with mock.patch('girder_worker.app._update_status') as us:
        task = mock.MagicMock()
        task.name = name
        gw_task_success(sender=task)
        us.assert_not_called()


@pytest.mark.parametrize('name', BUILTIN_CELERY_TASKS)
def test_gw_task_failure_with_builtin_tasks_should_noop(name):
    with mock.patch('girder_worker.app._update_status') as us:
        task = mock.MagicMock()
        task.name = name
        gw_task_failure(sender=task)
        us.assert_not_called()


def test_gw_task_prerun_applies_girder_api_url_env_override(monkeypatch):
    monkeypatch.setenv('GIRDER_WORKER_API_URL', 'http://worker-host/api/v1')

    task = mock.MagicMock()
    task.name = 'example.task'
    task.request.girder_api_url = 'http://server-host/api/v1'
    task.request.girder_client_token = 'token'
    task.request.jobInfoSpec = {
        'url': 'http://server-host/api/v1/job/jobid',
        'method': 'PUT',
        'logPrint': False,
    }
    task.request.headers = None

    with mock.patch('girder_worker.app.GirderClient') as GirderClient, \
            mock.patch('girder_worker.app._update_status'):
        gw_task_prerun(task=task, sender=task)

    assert task.request.girder_api_url == 'http://worker-host/api/v1'
    assert task.request.jobInfoSpec['url'] == 'http://worker-host/api/v1/job/jobid'
    GirderClient.assert_called_once_with(apiUrl='http://worker-host/api/v1')
    assert task.girder_client.token == 'token'
