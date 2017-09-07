from girder.api.rest import getApiUrl
from girder.utility.model_importer import ModelImporter


def jobInfoSpec(job, token=None, logPrint=True):
    """
    Build the jobInfo specification for a task to write status and log output
    back to a Girder job.

    :param job: The job document representing the worker task.
    :type job: dict
    :param token: The token to use. Creates a job token if not passed.
    :type token: str or dict
    :param logPrint: Whether standard output from the job should be
    """
    if token is None:
        token = ModelImporter.model('job', 'jobs').createJobToken(job)

    if isinstance(token, dict):
        token = token['_id']

    return {
        'method': 'PUT',
        'url': '/'.join((getApiUrl(), 'job', str(job['_id']))),
        'reference': str(job['_id']),
        'headers': {'Girder-Token': token},
        'logPrint': logPrint
    }
