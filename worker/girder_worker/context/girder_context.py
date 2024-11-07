from girder_worker.utils import _maybe_model_repr, _walk_obj


def create_task_job(job_defaults, sender=None, body=None,
                    exchange=None, routing_key=None, headers=None,
                    properties=None, declare=None, retry_policy=None,
                    **kwargs):

    from girder.utility.model_importer import ModelImporter
    from girder.api.rest import getCurrentUser
    from girder_plugin_worker import utils

    job_model = ModelImporter.model('job', 'jobs')

    user = headers.pop('girder_user', getCurrentUser())

    # Sanitize any Transform objects
    task_args = tuple(_walk_obj(body[0], _maybe_model_repr))
    task_kwargs = _walk_obj(body[1], _maybe_model_repr)

    job = job_model.createJob(
        **{'title': headers.pop('girder_job_title',
                                job_defaults.get('girder_job_title', '')),
           'type': headers.pop('girder_job_type',
                               job_defaults.get('girder_job_type', '')),
           'handler': headers.pop('girder_job_handler',
                                  job_defaults.get('girder_job_handler', '')),
           'public': headers.pop('girder_job_public',
                                 job_defaults.get('girder_job_public', '')),
           'user': user,
           'args': task_args,
           'kwargs': task_kwargs,
           'otherFields': dict(
               celeryTaskId=headers['id'],
               **headers.pop('girder_job_other_fields',
                             job_defaults.get('girder_job_other_fields', '')))})

    headers['jobInfoSpec'] = utils.jobInfoSpec(job)
    return job


def attach_girder_api_url(sender=None, body=None, exchange=None,
                          routing_key=None, headers=None, properties=None,
                          declare=None, retry_policy=None, **kwargs):
    from girder_plugin_worker import utils
    headers['girder_api_url'] = utils.getWorkerApiUrl()


def attach_girder_client_token(sender=None, body=None, exchange=None,
                               routing_key=None, headers=None, properties=None,
                               declare=None, retry_policy=None, **kwargs):
    from girder.utility.model_importer import ModelImporter
    from girder.api.rest import getCurrentUser
    token_model = ModelImporter.model('token')
    scope = 'jobs.rest.create_job'
    try:
        token = token_model.createToken(scope=scope, user=user)
    except NameError:
        token = token_model.createToken(scope=scope, user=getCurrentUser())
    headers['girder_client_token'] = token['_id']


def get_async_result_job_property(async_result):
    # GirderAsyncResult() objects may be instantiated in
    # either a girder REST request, or in some other
    # context (e.g. from a running girder_worker instance
    # if there is a chain).  If we are in a REST request
    # we should have access to the girder package and can
    # directly access the database If we are in a
    # girder_worker context (or even in python console or
    # a testing context) then we should get an ImportError
    # and we can make a REST request to get the
    # information we need.
    from girder.utility.model_importer import ModelImporter
    job_model = ModelImporter.model('job', 'jobs')

    try:
        return job_model.findOne({'celeryTaskId': async_result.task_id})
    except IndexError:
        return None
