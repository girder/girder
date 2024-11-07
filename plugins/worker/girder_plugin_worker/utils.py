#!/usr/bin/env python

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from .constants import PluginSettings
from girder.api.rest import getApiUrl
from girder.exceptions import FilePathException
from girder.models.file import File
from girder.models.setting import Setting
from girder.utility import setting_utilities
from girder_jobs.models.job import Job


@setting_utilities.validator({
    PluginSettings.BROKER,
    PluginSettings.BACKEND
})
def validateSettings(doc):
    """
    Handle plugin-specific system settings. Right now we don't do any
    validation for the broker or backend URL settings, but we do reinitialize
    the celery app object with the new values.
    """
    global _celeryapp
    _celeryapp = None


def getWorkerApiUrl():
    """
    Return the API base URL to which the worker should callback to
    write output information back to the server. This is controlled
    via a system setting, and the default is to use the core server
    root setting.
    """
    apiUrl = Setting().get(PluginSettings.API_URL)
    return apiUrl or getApiUrl()


def girderInputSpec(resource, resourceType='file', name=None, token=None,
                    dataType='string', dataFormat='text', fetchParent=False):
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
    :param fetchParent: Whether to fetch the whole parent resource of the
        specified resource as a side effect.
    :type fetchParent: bool
    """
    if isinstance(token, dict):
        token = token['_id']

    result = {
        'mode': 'girder',
        'api_url': getWorkerApiUrl(),
        'token': token,
        'id': str(resource['_id']),
        'name': name or resource['name'],
        'resource_type': resourceType,
        'type': dataType,
        'format': dataFormat,
        'fetch_parent': fetchParent
    }

    if resourceType == 'file' and not fetchParent and Setting().get(PluginSettings.DIRECT_PATH):
        # If we are adding a file and it exists on the local filesystem include
        # that location.  This can permit the user of the specification to
        # access the file directly instead of downloading the file.
        try:
            result['direct_path'] = File().getLocalFilePath(resource)
        except FilePathException:
            pass
    return result


def girderOutputSpec(parent, token, parentType='folder', name=None,
                     dataType='string', dataFormat='text', reference=None):
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
    :param reference: Optional "reference" string to pass back to the server
        during the upload. This can be used to attach arbitrary data to this
        for tracking purposes, e.g., referring back to related inputs. Bind to
        the "data.process" event to hook into the upload and inspect references.
    :type reference: str
    """
    if isinstance(token, dict):
        token = token['_id']

    return {
        'mode': 'girder',
        'api_url': getWorkerApiUrl(),
        'token': token,
        'name': name,
        'parent_id': str(parent['_id']),
        'parent_type': parentType,
        'type': dataType,
        'format': dataFormat,
        'reference': reference
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
        token = Job().createJobToken(job)

    if isinstance(token, dict):
        token = token['_id']

    return {
        'method': 'PUT',
        'url': '/'.join((getWorkerApiUrl(), 'job', str(job['_id']))),
        'reference': str(job['_id']),
        'headers': {'Girder-Token': token},
        'logPrint': logPrint
    }
