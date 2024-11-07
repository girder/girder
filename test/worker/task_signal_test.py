import sys
import unittest
from contextlib import contextmanager

from girder_worker.app import (
    girder_before_task_publish,
    gw_task_failure,
    gw_task_postrun,
    gw_task_prerun,
    gw_task_revoked,
    gw_task_success)

from girder_worker.utils import BUILTIN_CELERY_TASKS, JobStatus
from unittest import mock
import pytest
import requests


@contextmanager
def mock_worker_plugin_utils():
    """girder.plugins is not available unless you are
    working within the context of a rest request. This
    context manager allows us to mock girder.plugins.worker.utils
    without seting up a whole server.
    """
    with mock.patch('girder_worker.girder_plugin.utils') as utils:
        yield utils


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


class MockHTTPError(requests.HTTPError):
    def __init__(self, status_code, json_response):
        self.response = mock.MagicMock()
        self.response.status_code = status_code
        self.response.json.return_value = json_response


class TestSignals(unittest.TestCase):
    def setUp(self):
        self.headers = {
            'jobInfoSpec': {
                'method': 'PUT',
                'url': 'http://girder:8888/api/v1',
                'reference': 'JOBINFOSPECREFERENCE',
                'headers': {'Girder-Token': 'GIRDERTOKEN'},
                'logPrint': True
            }
        }

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_with_jobinfospec_no_job_created(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers=self.headers)

        create_job = mi.model.return_value.createJob
        with mock.patch('cherrypy.request.app', return_value=True):
            with mock_worker_plugin_utils():
                girder_before_task_publish(**inputs)

        gcu.assert_called_once()
        self.assertTrue(not create_job.called)

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_called_with_no_headers_create_job_inputs(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID'})

        create_job = mi.model.return_value.createJob
        with mock.patch('cherrypy.request.app', return_value=True):
            with mock_worker_plugin_utils():
                girder_before_task_publish(**inputs)

        # gcu.assert_called_once()
        create_job.assert_called_once_with(
            **{'title': '<unnamed job>',
               'type': 'celery',
               'handler': 'celery_handler',
               'public': False,
               'user': gcu.return_value,
               'args': (),
               'kwargs': {},
               'otherFields': {'celeryTaskId': 'CELERY-ASYNCRESULT-ID'}})

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_called_with_headers_create_job_inputs(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID',
                               'girder_job_title': 'GIRDER_JOB_TITLE',
                               'girder_job_type': 'GIRDER_JOB_TYPE',
                               'girder_job_handler': 'GIRDER_JOB_HANDLER',
                               'girder_job_public': 'GIRDER_JOB_PUBLIC',
                               'girder_job_other_fields': {'SOME_OTHER': 'FIELD'}})

        create_job = mi.model.return_value.createJob
        with mock.patch('cherrypy.request.app', return_value=True):
            with mock_worker_plugin_utils():
                girder_before_task_publish(**inputs)

        # gcu.assert_called_once()
        create_job.assert_called_once_with(
            **{'title': 'GIRDER_JOB_TITLE',
               'type': 'GIRDER_JOB_TYPE',
               'handler': 'GIRDER_JOB_HANDLER',
               'public': 'GIRDER_JOB_PUBLIC',
               'user': gcu.return_value,
               'args': (),
               'kwargs': {},
               'otherFields': {'celeryTaskId': 'CELERY-ASYNCRESULT-ID',
                               'SOME_OTHER': 'FIELD'}})

    @mock.patch('girder.utility.model_importer.ModelImporter')
    @mock.patch('girder.api.rest.getCurrentUser')
    def test_girder_before_task_publish_jobinfospec_called(self, gcu, mi):

        inputs = dict(sender='test.task',
                      # args, kwargs, options
                      body=[(), {}, {}],
                      headers={'id': 'CELERY-ASYNCRESULT-ID'})

        with mock.patch('cherrypy.request.app', return_value=True):
            with mock_worker_plugin_utils() as utils:
                girder_before_task_publish(**inputs)

                utils.jobInfoSpec.asset_called_once()
                utils.getWorkerApiUrl.assert_called_once()

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_prerun(self, jm):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.jobInfoSpec = self.headers['jobInfoSpec']
        task.request.parent_id = None

        gw_task_prerun(task=task, sender=task)

        task.job_manager.updateStatus.assert_called_once_with(
            JobStatus.RUNNING)

    @mock.patch('girder_worker.app.is_revoked')
    @mock.patch('girder_worker.utils.JobManager')
    def test_task_success(self, jm, is_revoked):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)
        is_revoked.return_value = False

        gw_task_success(sender=task)

        task.job_manager.updateStatus.assert_called_once_with(
            JobStatus.SUCCESS)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_failure(self, jm):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)

        exc, tb = mock.MagicMock(), mock.MagicMock()
        exc.__str__.return_value = 'MOCKEXCEPTION'

        with mock.patch('girder_worker.app.tb') as traceback:
            traceback.format_tb.return_value = 'TRACEBACK'

            gw_task_failure(sender=task, exception=exc, traceback=tb)

            task.job_manager.write.assert_called_once_with(
                'MagicMock: MOCKEXCEPTION\nTRACEBACK')
            task.job_manager.updateStatus(JobStatus.ERROR)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_postrun(self, jm):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.parent_id = None
        task.job_manager = jm(**self.headers)

        gw_task_postrun(task=task, sender=task)

        task.job_manager._flush.assert_called_once()

    @mock.patch('girder_worker.utils.JobManager.refreshStatus')
    def test_task_prerun_canceling(self, refreshStatus):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.jobInfoSpec = self.headers['jobInfoSpec']
        task.request.parent_id = None

        validation_error = {
            'field': 'status',
            'message': 'invalid state'
        }

        class SessionMock(requests.Session):

            def __init__(self, *args, **kwargs):
                self.request = mock.MagicMock()
                self.response = self.request.return_value
                self.response.raise_for_status.side_effect = [
                    MockHTTPError(400, validation_error), None]
                self.adapters = {}

        with unittest.mock.patch(
            'girder_worker.utils.requests.Session'
        ) as session:
            sessionMock = SessionMock()
            session.return_value = sessionMock

            refreshStatus.return_value = JobStatus.CANCELING

            gw_task_prerun(task=task, sender=task)

            refreshStatus.assert_called_once()
            self.assertEqual(
                sessionMock.request.call_args_list[0][1]['data']['status'], JobStatus.RUNNING)

            # Now try with QUEUED
            sessionMock.request.reset_mock()
            refreshStatus.reset_mock()
            sessionMock.response.raise_for_status.side_effect = [None]
            refreshStatus.return_value = JobStatus.QUEUED

            gw_task_prerun(task=task, sender=task)

            refreshStatus.assert_not_called()
            self.assertEqual(
                sessionMock.request.call_args_list[0][1]['data']['status'], JobStatus.RUNNING)

    @mock.patch('girder_worker.app.is_revoked')
    @mock.patch('girder_worker.utils.JobManager.refreshStatus')
    def test_task_success_canceling(self, refreshStatus, is_revoked):
        task = mock.MagicMock()
        task.name = 'example.task'
        task.request.jobInfoSpec = self.headers['jobInfoSpec']
        task.request.parent_id = None

        validation_error = {
            'field': 'status',
            'message': 'invalid'
        }

        class SessionMock(requests.Session):

            def __init__(self, *args, **kwargs):
                self.request = mock.MagicMock()
                self.response = self.request.return_value
                self.response.raise_for_status.side_effect = [
                    None, MockHTTPError(400, validation_error)]
                self.adapters = {}

        with unittest.mock.patch(
            'girder_worker.utils.requests.Session'
        ) as session:
            sessionMock = SessionMock()
            session.return_value = sessionMock

            refreshStatus.return_value = JobStatus.CANCELING
            is_revoked.return_value = True

            gw_task_prerun(task=task, sender=task)
            gw_task_success(sender=task)

            # We where in the canceling state so we should move into CANCELED
            refreshStatus.assert_called_once()
            self.assertEqual(
                sessionMock.request.call_args_list[1][1]['data']['status'], JobStatus.CANCELED)

            # Now try with RUNNING
            sessionMock.request.reset_mock()
            is_revoked.return_value = False
            refreshStatus.reset_mock()
            sessionMock.response.raise_for_status.side_effect = [None, None]

            gw_task_prerun(task=task, sender=task)
            gw_task_success(sender=task)

            # We should move into SUCCESS
            refreshStatus.assert_not_called()
            self.assertEqual(
                sessionMock.request.call_args_list[1][1]['data']['status'], JobStatus.SUCCESS)

    @mock.patch('girder_worker.utils.JobManager')
    def test_task_revoke(self, jm):
        task = mock.MagicMock()
        task.name = 'example.task'
        request = mock.MagicMock()
        request.message.headers = {
            'jobInfoSpec': self.headers['jobInfoSpec']
        }
        task.request.parent_id = None

        gw_task_revoked(sender=task, request=request)

        task.job_manager.updateStatus.assert_called_once_with(JobStatus.CANCELED)


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
