import os
import sys

import traceback as tb
from distutils.version import LooseVersion

from celery import Celery, __version__

from celery.signals import (
    before_task_publish,
    task_failure,
    task_postrun,
    task_prerun,
    task_revoked,
    task_success,
    worker_ready)


from girder_client import GirderClient

from girder_worker import logger
from girder_worker.context import get_context
from girder_worker.entrypoint import discover_tasks
from girder_worker.task import Task
from girder_worker.utils import (
    JobSpecNotFound,
    JobStatus,
    StateTransitionException,
    _job_manager,
    _update_status,
    is_builtin_celery_task,
    is_revoked
)
from girder_worker.utils.transform import ResultTransform

import jsonpickle
from kombu.serialization import register


@before_task_publish.connect  # noqa: C901
def girder_before_task_publish(sender=None, body=None, exchange=None,
                               routing_key=None, headers=None, properties=None,
                               declare=None, retry_policy=None, **kwargs):

    if is_builtin_celery_task(sender):
        return

    job = None

    try:
        context = get_context()
        if 'jobInfoSpec' not in headers:
            job = context.create_task_job(
                Task.girder_job_defaults(), sender=sender, body=body, exchange=exchange,
                routing_key=routing_key, headers=headers, properties=properties, declare=declare,
                retry_policy=retry_policy, **kwargs)

        if 'girder_api_url' not in headers:
            context.attach_girder_api_url(sender=sender, body=body,
                                          exchange=exchange,
                                          routing_key=routing_key,
                                          headers=headers,
                                          properties=properties,
                                          declare=declare,
                                          retry_policy=retry_policy,
                                          **kwargs)

        if 'girder_client_token' not in headers:
            context.attach_girder_client_token(sender=sender,
                                               body=body,
                                               exchange=exchange,
                                               routing_key=routing_key,
                                               headers=headers,
                                               properties=properties,
                                               declare=declare,
                                               retry_policy=retry_policy,
                                               **kwargs)
        if 'girder_result_hooks' in headers:
            if job is not None:
                for result_hook in headers['girder_result_hooks']:
                    if isinstance(result_hook, ResultTransform):
                        result_hook.job = job

            # Celery task headers are not automatically serialized by celery
            # before being passed off to ampq for byte packing. We will have
            # to do that here.
            p = jsonpickle.pickler.Pickler()
            headers['girder_result_hooks'] = \
                [p.flatten(grh) for grh in headers['girder_result_hooks']]

        # Finally,  remove all reserved_options from headers
        for key in Task.reserved_options:
            headers.pop(key, None)
    except Exception:
        logger.exception('An error occurred in girder_before_task_publish.')
        raise


@worker_ready.connect
def check_celery_version(*args, **kwargs):
    if LooseVersion(__version__) < LooseVersion('4.0.0'):
        sys.exit("""You are running Celery {}.

girder-worker requires celery>=4.0.0""".format(__version__))


@task_prerun.connect
def gw_task_prerun(task=None, sender=None, task_id=None,
                   args=None, kwargs=None, **rest):
    """Deserialize the jobInfoSpec passed in through the headers.

    This provides the a JobManager class as an attribute of the
    task before task execution.  decorated functions may bind to
    their task and have access to the job_manager for logging and
    updating their status in girder.
    """
    if is_builtin_celery_task(sender.name):
        return

    try:
        task.job_manager = _job_manager(task.request, task.request.headers)
        _update_status(task, JobStatus.RUNNING)

    except JobSpecNotFound:
        task.job_manager = None
        logger.warning('No jobInfoSpec. Setting job_manager to None.')
    except StateTransitionException:
        # Fetch the current status of the job
        status = task.job_manager.refreshStatus()
        # If we are canceling we want to stay in that state
        if status != JobStatus.CANCELING:
            raise

    try:
        task.girder_client = GirderClient(apiUrl=task.request.girder_api_url)
        task.girder_client.token = task.request.girder_client_token
    except AttributeError:
        task.girder_client = None

    # Deserialize girder_result_hooks if they exist
    if hasattr(task.request, 'girder_result_hooks'):
        u = jsonpickle.unpickler.Unpickler()
        task.request.girder_result_hooks = \
            [u.restore(grh) for grh in task.request.girder_result_hooks]


@task_success.connect
def gw_task_success(sender=None, **rest):
    if is_builtin_celery_task(sender.name):
        return

    try:
        if is_revoked(sender):
            _update_status(sender, JobStatus.CANCELED)
        else:
            _update_status(sender, JobStatus.SUCCESS)
    except AttributeError:
        pass
    except StateTransitionException:
        # Fetch the current status of the job
        status = sender.job_manager.refreshStatus()
        # If we are in CANCELING move to CANCELED
        if status == JobStatus.CANCELING or is_revoked(sender):
            _update_status(sender, JobStatus.CANCELED)
        else:
            raise


@task_failure.connect
def gw_task_failure(sender=None, exception=None,
                    traceback=None, **rest):
    if is_builtin_celery_task(sender.name):
        return

    try:

        msg = '%s: %s\n%s' % (
            exception.__class__.__name__, exception,
            ''.join(tb.format_tb(traceback)))

        sender.job_manager.write(msg)
        _update_status(sender, JobStatus.ERROR)

    except AttributeError:
        pass


@task_postrun.connect
def gw_task_postrun(task=None, sender=None, task_id=None,
                    args=None, kwargs=None,
                    retval=None, state=None, **rest):
    try:
        task.job_manager._flush()
    except AttributeError:
        pass
    finally:
        # Release stdout/stderr
        if hasattr(task, 'job_manager') and \
           hasattr(task.job_manager, 'cleanup') and \
           callable(task.job_manager.cleanup):
            task.job_manager.cleanup()


@task_revoked.connect
def gw_task_revoked(sender=None, request=None, **rest):
    try:
        sender.job_manager = _job_manager(headers=request.message.headers,
                                          kwargs=request.kwargsrepr)
        _update_status(sender, JobStatus.CANCELED)
    except AttributeError:
        pass
    except JobSpecNotFound:
        logger.warning(
            "No jobInfoSpec. Unable to move \'%s\' into CANCELED state.")


register('girder_io', jsonpickle.encode, jsonpickle.decode,
         content_type='application/json',
         content_encoding='utf-8')

app = Celery(
    main=os.environ.get('GIRDER_WORKER_CELERY_APP_MAIN', 'app_main'),
    task_cls='girder_worker.task:Task')

discover_tasks(app)

app.config_from_object('girder_worker.celeryconfig', force=True)
