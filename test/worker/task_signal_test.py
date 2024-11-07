import sys
from contextlib import contextmanager

from girder_worker.app import (
    girder_before_task_publish,
    gw_task_failure,
    gw_task_prerun,
    gw_task_success)

from girder_worker.utils import BUILTIN_CELERY_TASKS
from unittest import mock
import pytest


@contextmanager
def girder_not_importable():
    """Girder should not be importable to test celery context
    specific logic
    """
    girder = sys.modules.get('girder')
    model_importer = sys.modules.get('girder.utility.model_importer')
    sys.modules['girder'] = None
    sys.modules['girder.utility.model_importer'] = None
    yield
    sys.modules['girder'] = girder
    sys.modules['girder.utility.model_importer'] = model_importer


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


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_current_task(warn):
    with girder_not_importable():
        inputs = dict(
            sender='example.task',
            headers={
                'girder_api_url': 'url',
                'girder_client_token': 'token',
                'id': 'id'
            }
        )

        girder_before_task_publish(**inputs)
        warn.assert_called_with('Girder job not created: Parent task is None')


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_current_task_request(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request = None
            inputs = dict(
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            warn.assert_called_with("Girder job not created: Parent task's request is None")


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_api_url_in_request(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            delattr(mocked_app.current_task.request, 'girder_api_url')
            inputs = dict(
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            warn.assert_called_with(
                "Girder job not created: Parent task's request does not contain girder_api_url")


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_token_in_request(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            delattr(mocked_app.current_task.request, 'girder_client_token')
            inputs = dict(
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            m = "Girder job not created: Parent task's request does not contain girder_client_token"
            warn.assert_called_with(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_id_in_request(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            delattr(mocked_app.current_task.request, 'id')
            inputs = dict(
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            m = "Girder job not created: Parent task's request does not contain id"
            warn.assert_called_with(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_id_in_haeders(warn):
    with girder_not_importable():
        # mocked_app object needs to be in the context for testing
        with mock.patch('girder_worker.context.nongirder_context.current_app'):

            inputs = dict(
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token'
                }
            )
            girder_before_task_publish(**inputs)
            warn.assert_called_with('Girder job not created: id is not in headers')


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_gc_fails(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request.id = 'id'
            mocked_app.current_task.request.girder_api_url = 'url'
            inputs = dict(
                body=[(), {}, {}],
                sender='example.task',
                headers={
                    'girder_api_url': 'url',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            assert warn.call_args[0][0].startswith('Failed to post job: Invalid URL')


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_api_url_in_headers(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request.id = 'id'
            delattr(mocked_app.current_task.request, 'girder_api_url')
            inputs = dict(
                body=[(), {}, {}],
                sender='example.task',
                headers={
                    'jobInfoSpec': 'jobInfoSpec',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            m = 'Could not get girder_api_url from parent task'
            assert warn.call_args[0][0].startswith(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_parent_task_no_api_url(warn):
    with girder_not_importable():
        inputs = dict(
            body=[(), {}, {}],
            sender='example.task',
            headers={
                'jobInfoSpec': 'jobInfoSpec',
                'girder_client_token': 'token',
                'id': 'id'
            }
        )
        girder_before_task_publish(**inputs)
        m = 'Could not get girder_api_url from parent task: Parent task is None'
        warn.assert_called_with(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_parent_task_request_no_api_url(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request = None
            inputs = dict(
                body=[(), {}, {}],
                sender='example.task',
                headers={
                    'jobInfoSpec': 'jobInfoSpec',
                    'girder_client_token': 'token',
                    'id': 'id'
                }
            )

            girder_before_task_publish(**inputs)
            m = "Could not get girder_api_url from parent task: Parent task's request is None"
            warn.assert_called_with(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_token_in_headers(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request.id = 'id'
            delattr(mocked_app.current_task.request, 'girder_client_token')
            inputs = dict(
                body=[(), {}, {}],
                sender='example.task',
                headers={
                    'jobInfoSpec': 'jobInfoSpec',
                    'girder_api_url': 'url',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            m = 'Could not get token from parent task'
            assert warn.call_args[0][0].startswith(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_parent_task_no_token(warn):
    with girder_not_importable():
        inputs = dict(
            body=[(), {}, {}],
            sender='example.task',
            headers={
                'jobInfoSpec': 'jobInfoSpec',
                'girder_api_url': 'url',
                'id': 'id'
            }
        )
        girder_before_task_publish(**inputs)
        m = 'Could not get token from parent task: Parent task is None'
        warn.assert_called_with(m)


@mock.patch('girder_worker.logger.warn')
def test_girder_before_task_publish_celery_context_no_parent_task_request_no_token(warn):
    with girder_not_importable():
        with mock.patch('girder_worker.context.nongirder_context.current_app') as mocked_app:
            mocked_app.current_task.request = None
            inputs = dict(
                body=[(), {}, {}],
                sender='example.task',
                headers={
                    'jobInfoSpec': 'jobInfoSpec',
                    'girder_api_url': 'token',
                    'id': 'id'
                }
            )
            girder_before_task_publish(**inputs)
            m = "Could not get token from parent task: Parent task's request is None"
            warn.assert_called_with(m)
