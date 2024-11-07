from girder_worker.app import (
    girder_before_task_publish,
    gw_task_failure,
    gw_task_prerun,
    gw_task_success)

from girder_worker.utils import BUILTIN_CELERY_TASKS
from unittest import mock
import pytest


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
