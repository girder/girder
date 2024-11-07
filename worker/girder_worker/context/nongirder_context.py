import json
from celery import current_app
from girder_client import GirderClient
from girder_worker import logger
from girder_worker.utils import _maybe_model_repr, _walk_obj

import requests


class MissingJobArguments(RuntimeError):
    pass


def create_task_job(job_defaults, sender=None, body=None,
                    exchange=None, routing_key=None, headers=None,
                    properties=None, declare=None, retry_policy=None,
                    **kwargs):
    parent_task = current_app.current_task
    try:
        if parent_task is None:
            raise MissingJobArguments('Parent task is None')
        if parent_task.request is None:
            raise MissingJobArguments("Parent task's request is None")
        if not hasattr(parent_task.request, 'girder_api_url'):
            raise MissingJobArguments(
                "Parent task's request does not contain girder_api_url")
        if not hasattr(parent_task.request, 'girder_client_token'):
            raise MissingJobArguments(
                "Parent task's request does not contain girder_client_token")
        if not hasattr(parent_task.request, 'id'):
            raise MissingJobArguments(
                "Parent task's request does not contain id")
        if 'id' not in headers:
            raise MissingJobArguments('id is not in headers')

        gc = GirderClient(apiUrl=parent_task.request.girder_api_url)
        gc.token = parent_task.request.girder_client_token

        task_args = tuple(_walk_obj(body[0], _maybe_model_repr))
        task_kwargs = _walk_obj(body[1], _maybe_model_repr)
        parameters = {
            'title': headers.pop('girder_job_title',
                                 job_defaults.get('girder_job_title', '')),
            'type': headers.pop('girder_job_type',
                                job_defaults.get('girder_job_type', '')),
            'handler': headers.pop('girder_job_handler',
                                   job_defaults.get('girder_job_handler', '')),
            'public': headers.pop('girder_job_public',
                                  job_defaults.get('girder_job_public', '')),
            'args': json.dumps(task_args),
            'kwargs': task_kwargs,
            'otherFields': json.dumps(
                dict(celeryTaskId=headers['id'],
                     celeryParentTaskId=parent_task.request.id,
                     **headers.pop('girder_job_other_fields',
                                   job_defaults.get('girder_job_other_fields', ''))))
        }

        try:
            response = gc.post('job', parameters=parameters, jsonResp=False)
            if response.ok:
                headers['jobInfoSpec'] = response.json().get('jobInfoSpec')
                return response.json()
        except requests.exceptions.RequestException as e:
            logger.warn(f'Failed to post job: {e}')

    except MissingJobArguments as e:
        logger.warn(f'Girder job not created: {str(e)}')


def attach_girder_api_url(sender=None, body=None, exchange=None,
                          routing_key=None, headers=None, properties=None,
                          declare=None, retry_policy=None, **kwargs):
    parent_task = current_app.current_task
    try:
        if parent_task is None:
            raise MissingJobArguments('Parent task is None')
        if parent_task.request is None:
            raise MissingJobArguments("Parent task's request is None")
        if not hasattr(parent_task.request, 'girder_api_url'):
            raise MissingJobArguments(
                "Parent task's request does not contain girder_api_url")
        headers['girder_api_url'] = parent_task.request.girder_api_url
    except MissingJobArguments as e:
        logger.warn(f'Could not get girder_api_url from parent task: {str(e)}')


def attach_girder_client_token(sender=None, body=None, exchange=None,
                               routing_key=None, headers=None, properties=None,
                               declare=None, retry_policy=None, **kwargs):
    parent_task = current_app.current_task
    try:
        if parent_task is None:
            raise MissingJobArguments('Parent task is None')
        if parent_task.request is None:
            raise MissingJobArguments("Parent task's request is None")
        if not hasattr(parent_task.request, 'girder_client_token'):
            raise MissingJobArguments(
                "Parent task's request does not contain girder_client_token")

        headers['girder_client_token'] = parent_task.request.girder_client_token
    except MissingJobArguments as e:
        logger.warn(f'Could not get token from parent task: {str(e)}')


def get_async_result_job_property(async_result):
    # NOT IMPLEMENTED!
    return None
