from girder.api.rest import getApiUrl
from girder.utility.model_importer import ModelImporter


def girderInputSpec(resource, resourceType='file', name=None, token=None,
                    dataType='string', dataFormat='text'):
    """
    Downstream plugins that are building Girder worker jobs that use Girder IO
    should use this to generate the input specs more easily.

    :param resource: The resource document to be downloaded at runtime.
    :type resource: dict
    :param resourceType: The resource type to download for the input. Should
        be "folder", "item", or "file".
    :type resourceType: str
    :param name: The name of the resource to download. If not passed, uses
        the "name" field of the resource document.
    :type name: str or None
    :param token: The Girder token document or raw token string to use to
        authenticate when downloading. Pass `None` for anonymous downloads.
    :type token: dict, str, or None
    :param dataType: The worker `type` field.
    :type dataType: str
    :param dataFormat: The worker `format` field.
    :type dataFormat: str
    """
    if isinstance(token, dict):
        token = token['_id']

    return {
        'mode': 'girder',
        'api_url': getApiUrl(),
        'token': token,
        'id': str(resource['_id']),
        'name': name or resource['name'],
        'resource_type': resourceType,
        'type': dataType,
        'format': dataFormat
    }


def girderOutputSpec(parent, token, parentType='folder', name=None,
                     dataType='string', dataFormat='text'):
    """
    Downstream plugins that are building worker jobs that use Girder IO
    should use this to generate the output specs more easily.

    :param parent: The parent to upload the data into (an item or folder).
    :type parent: dict
    :param token: The Girder token document or raw token string to use to
        authenticate when uploading.
    :type token: dict or str
    :param parentType: The type of the parent object ("item" or "folder").
    :type parentType: str
    :param name: Name of the resource to use when uploading. Required if
        the output target type is "memory". If the target is "filepath", uses
        the basename of the file being uploaded by default.
    :type name: str or None
    :param dataType: The worker `type` field.
    :type dataType: str
    :param dataFormat: The worker `format` field.
    :type dataFormat: str
    """
    if isinstance(token, dict):
        token = token['_id']

    return {
        'mode': 'girder',
        'api_url': getApiUrl(),
        'token': token,
        'name': name,
        'parent_id': str(parent['_id']),
        'parent_type': parentType,
        'type': dataType,
        'format': dataFormat
    }


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
