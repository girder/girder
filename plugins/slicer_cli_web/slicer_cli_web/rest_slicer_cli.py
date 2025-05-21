import copy
import itertools
import json
import logging
import threading
import time

import cherrypy
from bson.objectid import ObjectId
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, RestException, boundHandler, getApiUrl, getCurrentToken
from girder.constants import AccessType, SortDir
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from .cli_utils import (as_model, generate_description, get_cli_parameters, is_on_girder,
                        return_parameter_file_name)
from .models import CLIItem
from .prepare_task import FOLDER_SUFFIX, OPENAPI_DIRECT_TYPES, prepare_task

_return_parameter_file_desc = """
Filename in which to write simple return parameters (integer, float,
integer-vector, etc.) as opposed to bulk return parameters (image, file,
directory, geometry, transform, measurement, table).
"""

logger = logging.getLogger(__name__)


def stringifyParam(param):
    newparam = param.__class__()
    for key in param.__slots__:
        if key != 'typ':
            setattr(newparam, key, getattr(param, key, None))
    newparam.typ = 'string'
    return newparam


def _getParamDefaultVal(param):
    if param.default is not None:
        return param.default
    elif param.typ == 'boolean':
        return False
    elif param.isVector():
        return None
    elif param.isExternalType():
        return None
    elif param.typ == 'float' or param.typ == 'integer':
        return 0
    else:
        raise Exception(
            'optional parameters of type %s must provide a default value in the xml' % param.typ)


def _canBeBatched(param):
    return (
        param.isExternalType()
        and param.typ != 'directory'
        and not getattr(param, 'multiple', None)
        and param.channel != 'output')


def _addInputParamToHandler(param, handlerDesc, required=True):
    # add to route description
    desc = param.description
    dataType = 'string'
    enum = None
    schema = None

    if param.isExternalType():
        if _canBeBatched(param):
            desc = (
                'Girder ID of input %s (if batch input, this is a regex '
                'for item names) - %s: %s'
                % (param.typ, param.identifier(), param.description))
        else:
            desc = 'Girder ID of input %s - %s: %s' % (
                param.typ, param.identifier(), param.description)
    elif param.typ in OPENAPI_DIRECT_TYPES:
        dataType = param.typ
    elif param.typ == 'string-enumeration':
        enum = param.elements
    elif param.isVector():
        dataType = 'json'
        itemType = param.typ
        if param.typ == 'float' or param.typ == 'double':
            itemType = 'number'
        schema = dict(type='array', items=dict(type=itemType))
        desc = '%s as JSON (%s)' % (param.description, param.typ)
    else:
        dataType = 'json'
        desc = '%s as JSON (%s)' % (param.description, param.typ)

    defaultValue = None
    if not required or param.default is not None:
        defaultValue = _getParamDefaultVal(param)

    if dataType == 'json':
        handlerDesc.jsonParam(param.identifier(), desc,
                              default=defaultValue,
                              required=required, schema=schema)
    else:
        handlerDesc.param(param.identifier(), desc, dataType=dataType, enum=enum,
                          default=defaultValue,
                          required=required)
    if _canBeBatched(param):
        handlerDesc.param(
            param.identifier() + FOLDER_SUFFIX,
            'Girder ID of parent folder for batch input %s - %s: %s'
            % (param.typ, param.identifier(), param.description),
            dataType='string', required=False)


def _addOutputParamToHandler(param, handlerDesc, required=True):
    if not param.isExternalType():  # just files are supported
        return

    # add param for parent folder to route description
    handlerDesc.param(
        param.identifier() + FOLDER_SUFFIX,
        'Girder ID of parent folder for output %s - %s: %s'
        % (param.typ, param.identifier(), param.description),
        dataType='string', required=required)

    # add param for name of current output to route description

    defaultFileExtension = None
    try:
        defaultFileExtension = param.defaultExtension()
    except KeyError:  # file is not an EXTERNAL_TYPE in the parser
        if param.fileExtensions:
            defaultFileExtension = param.fileExtensions[0]

    if defaultFileExtension and '|' in defaultFileExtension:
        defaultFileExtension = defaultFileExtension.split('|')[0]

    defaultValue = ('%s%s' % (param.identifier(), defaultFileExtension)
                    if defaultFileExtension else None)
    handlerDesc.param(
        param.identifier(),
        'Name of output %s - %s: %s'
        % (param.typ, param.identifier(), param.description),
        default=defaultValue, dataType='string', required=required)


def _addReturnParameterFileParamToHandler(handlerDesc):

    curName = return_parameter_file_name
    curType = 'file'
    curDesc = _return_parameter_file_desc

    # add param for parent folder to route description
    handlerDesc.param(
        curName + FOLDER_SUFFIX,
        'Girder ID of parent folder for output %s - %s: %s'
        % (curType, curName, curDesc),
        dataType='string', required=False)

    # add param for name of current output to route description
    handlerDesc.param(
        curName,
        'Name of output %s - %s: %s' % (curType, curName, curDesc),
        dataType='string', required=False)


def batchCLIJob(cliItem, params, user, cliTitle):
    """
    Create a local asynchronous job to run a batch of other jobs.

    :param cliItem: a CLIItem model.
    :param params: parameter dictionary passed to the endpoint.
    :param user: user model for the current user.
    :param cliTitle: title of the job.
    :returns: a job model.
    """
    # We have to flog the girder_worker setting if it isn't set, since the task
    # will be run outside of a cherrypy request context, and therefore
    # girder_worker cannot determine the api_url.  Further girder_worker
    # doesn't expose its constants, so we have to use the string form.  There
    # is no way to confidently UNSET the setting, as two batches could be
    # running concurrently.
    if not Setting().get('worker.api_url'):
        Setting().set('worker.api_url', getApiUrl())
    # Note that this uses a local job to manage the sub-jobs, but all of the sub-jobs actually
    # execute in the worker via `direct_docker_run.run.delay`.
    job = Job().createLocalJob(
        module='slicer_cli_web.rest_slicer_cli',
        function='batchCLITask',
        kwargs={
            'cliItemId': str(cliItem._id),
            'params': params,
            'userId': user['_id'],
            'cliTitle': cliTitle,
            'url': cherrypy.url(),
        },
        title='Batch process %s' % cliTitle,
        type='slicer_cli_web_batch#%s#%s' % (cliItem.image, cliItem.name),
        user=user,
        public=True,
    )
    job['_original_params'] = params
    job['_original_name'] = cliItem.name
    job['_original_path'] = cliItem.restBasePath
    job = Job().save(job)
    Job().scheduleJob(job)
    return job


def batchCLITask(job):
    """
    Run a batch of jobs via a thread.

    :param job: the job model.
    """
    proc = threading.Thread(target=batchCLITaskProcess, args=(job,), daemon=True)
    proc.start()
    return job, proc


def batchCLITaskProcess(job):  # noqa C901
    """
    Run a batch of jobs.  The job parameters contain the id of the cli item,
    the parameters, including those for batching, and the user id.

    :param job: the job model.
    """
    params = job['kwargs']['params']
    cliTitle = job['kwargs']['cliTitle']
    user = User().load(job['kwargs']['userId'], force=True)
    token = Token().createToken(user=user)
    cliItem = CLIItem.find(job['kwargs']['cliItemId'], user)
    handler = genHandlerToRunDockerCLI(cliItem)
    batchParams = handler.getBatchParams(params)
    job = Job().updateJob(
        job, log='Started batch processing %s\n' % cliTitle,
        status=JobStatus.RUNNING)
    batchCursors = []
    count = None
    for param in batchParams:
        q = {
            'folderId': ObjectId(params.get(param.identifier() + FOLDER_SUFFIX)),
            'name': {'$regex': params.get(param.identifier())}
        }
        if param.typ == 'image':
            q['largeImage.fileId'] = {'$exists': True}
        cursor = Item().findWithPermissions(q, sort=[('lowerName', SortDir.ASCENDING)], user=user)
        batchCursors.append(cursor)
        if count is None:
            count = cursor.count()
        elif cursor.count() != count:
            job = Job().updateJob(
                job, log='Failed batch processing %s - different number '
                'of entries on batch inputs\n' % cliTitle,
                status=JobStatus.ERROR)
            return
    scheduled = 0
    done = False
    lastSubJob = None
    try:
        while not done or (lastSubJob and lastSubJob['status'] not in {
                JobStatus.CANCELED, JobStatus.ERROR, JobStatus.SUCCESS}):
            job = Job().load(id=job['_id'], force=True)
            if not job or job['status'] in {JobStatus.CANCELED, JobStatus.ERROR}:
                return
            lastSubJob = None if lastSubJob is None else Job().load(
                id=lastSubJob['_id'], force=True)
            if lastSubJob is None or lastSubJob['status'] not in {
                    JobStatus.QUEUED, JobStatus.INACTIVE}:
                jobParams = params.copy()
                paramText = []
                for idx, param in enumerate(batchParams):
                    try:
                        item = batchCursors[idx].next()  # noqa B305
                    except StopIteration:
                        item = None
                    if item is None:
                        done = True
                        break
                    if param.typ == 'file':
                        value = str(Item().childFiles(item, limit=1).next()['_id'])  # noqa B305
                    elif param.typ == 'image':
                        value = item['largeImage']['fileId']
                    else:
                        value = str(item['_id'])
                    jobParams.pop(param.identifier() + FOLDER_SUFFIX)
                    jobParams[param.identifier()] = value
                    paramText.append(', %s=%s' % (param.identifier(), value))
                if not done:
                    # We are running in a girder context, but girder_worker
                    # uses cherrypy.request.app to detect this, so we have to
                    # fake it.
                    _before = cherrypy.request.app
                    cherrypy.request.app = 'fake_context'
                    try:
                        lastSubJob = handler.subHandler(cliItem, jobParams, user, token).job
                    finally:
                        cherrypy.request.app = _before
                    scheduled += 1
                    Job().updateJob(
                        job, log='Scheduling job %s, %d/%d for %s%s\n' % (
                            lastSubJob['_id'], scheduled, count, cliTitle, ''.join(paramText)))
                    continue
            time.sleep(0.1)
    except Exception as exc:
        Job().updateJob(
            job, log='Error batch processing %s\n' % cliTitle,
            status=JobStatus.ERROR)
        logger.exception('Error batch processing %s\n' % cliTitle)
        Job().updateJob(job, log='Exception: %r\n' % exc)
        return
    Job().updateJob(
        job, log='Finished batch processing %s\n' % cliTitle,
        status=JobStatus.SUCCESS)


def genHandlerToRunDockerCLI(cliItem):  # noqa C901
    """
    Generates a handler to run docker CLI using girder_worker

    :param cliItem: a CLIItem model.
    :returns: a function that runs the CLI using girder_worker
    """
    itemId = cliItem._id

    clim = as_model(cliItem.xml)
    cliTitle = clim.title

    # set a description for the REST endpoint for the CLI
    handlerDesc = Description(clim.title) \
        .notes(generate_description(clim)) \
        .produces('application/json')

    # get CLI parameters
    index_params, opt_params, simple_out_params = get_cli_parameters(clim)

    datalist = {}

    for param in index_params:
        if param.channel == 'output':
            _addOutputParamToHandler(param, handlerDesc, True)
        else:
            _addInputParamToHandler(param, handlerDesc, True)
            if param.datalist:
                datalist[param.name] = {'json': json.loads(param.datalist)}
    for param in opt_params:
        if param.channel == 'output':
            _addOutputParamToHandler(param, handlerDesc, False)
        else:
            _addInputParamToHandler(param, handlerDesc, False)
            if param.datalist:
                datalist[param.name] = {'json': json.loads(param.datalist)}

    # add returnparameterfile if there are simple output params
    has_simple_return_file = len(simple_out_params) > 0
    if has_simple_return_file:
        _addReturnParameterFileParamToHandler(handlerDesc)

    def getBatchParams(params):
        """
        Return a list of parameters that will be used in a batch job.  The list
        is empty for non-batch jobs.

        :param params: the parameters as passed to the endpoint.
        :returns: a list of batch parameters from the cli (not their values).
        """
        batchParams = []
        for param in itertools.chain(index_params, opt_params):
            if _canBeBatched(param) and params.get(param.identifier() + FOLDER_SUFFIX):
                batchParams.append(param)
        return batchParams

    def cliSubHandler(currentItem, params, user, token, datalist=None):
        """
        Create a job for a Slicer CLI item and schedule it.

        :param currentItem: a CLIItem model.
        :param params: parameter dictionary passed to the endpoint.
        :param user: user model for the current user.
        :param token: allocated token for the job.
        :param datalist: if not None, an object with keys that override
            parameters.  No outputs are used.
        """
        from .girder_worker_plugin.direct_docker_run import run

        original_params = copy.deepcopy(params)
        if hasattr(getCurrentToken, 'set'):
            getCurrentToken.set(token)
        if not getCurrentToken():
            cherrypy.request.headers['Girder-Token'] = token['_id']

        container_args = [cliItem.name]
        reference = {'slicer_cli_web': {
            'title': cliTitle,
            'image': cliItem.image,
            'name': cliItem.name,
        }}
        now = time.localtime()
        templateParams = {
            'title': cliTitle,  # e.g., "Detects Nuclei"
            'task': cliItem.name,  # e.g., "NucleiDetection"
            'image': cliItem.image,  # e.g., "dsarchive/histomicstk:latest"
            'now': time.strftime('%Y%m%d-%H%M%S', now),
            'yyyy': time.strftime('%Y', now),
            'mm': time.strftime('%m', now),
            'dd': time.strftime('%d', now),
            'HH': time.strftime('%H', now),
            'MM': time.strftime('%M', now),
            'SS': time.strftime('%S', now),
        }

        sub_index_params, sub_opt_params = index_params, opt_params
        if datalist:
            params = params.copy()
            params.update(datalist)
            sub_index_params = [
                param if param.name not in datalist or not is_on_girder(param)
                else stringifyParam(param)
                for param in index_params
                if (param.name not in datalist or datalist.get(param.name) is not None)
                and param.name not in {k + FOLDER_SUFFIX for k in datalist}]
            sub_opt_params = [
                param if param.name not in datalist or not is_on_girder(param)
                else stringifyParam(param)
                for param in opt_params
                if param.channel != 'output' and (
                    param.name not in datalist or datalist.get(param.name) is not None)
                and param.name not in {k + FOLDER_SUFFIX for k in datalist}]

        args, result_hooks, primary_input_name = prepare_task(
            params, user, token, sub_index_params, sub_opt_params,
            has_simple_return_file and not datalist,
            reference, templateParams=templateParams)
        container_args.extend(args)

        jobType = '%s#%s' % (cliItem.image, cliItem.name)

        if primary_input_name:
            jobTitle = '%s on %s' % (cliTitle, primary_input_name)
        else:
            jobTitle = cliTitle

        job_kwargs = cliItem.item.get('meta', {}).get('docker-params', {})
        job = run.delay(
            girder_user=user,
            girder_job_type=jobType,
            girder_job_title=jobTitle,
            girder_result_hooks=result_hooks,
            image=cliItem.digest,
            pull_image='if-not-present',
            container_args=container_args,
            **job_kwargs
        )
        jobRecord = Job().load(job.job['_id'], force=True)
        job.job['_original_params'] = jobRecord['_original_params'] = original_params
        job.job['_original_name'] = jobRecord['_original_name'] = cliItem.name
        job.job['_original_path'] = jobRecord['_original_path'] = cliItem.restBasePath
        Job().save(jobRecord)
        return job

    @access.token
    @describeRoute(handlerDesc)
    def cliHandler(resource, params):
        user = resource.getCurrentUser()
        token = resource.getCurrentToken()
        try:
            from girder_jobs.constants import REST_CREATE_JOB_TOKEN_SCOPE

            if (user is None and token and token.get('access', {})
                    and len(token['access'].get('users', [])) == 1):
                Token().requireScope(token, REST_CREATE_JOB_TOKEN_SCOPE)
                user = User().load(id=token['access']['users'][0]['id'], force=True)
        except Exception:
            pass
        currentItem = CLIItem.find(itemId, user)
        if not currentItem:
            raise RestException('Invalid CLI Item id (%s).' % (itemId))
        # Create a new token for this job; otherwise, the user could log out
        # and the job would fail to finish.  We may want to override the
        # duration of this token (it defaults to the setting for cookie
        # lifetime).
        batchParams = getBatchParams(params)
        if len(batchParams):
            job = batchCLIJob(currentItem, params, user, cliTitle)
        else:
            token = Token().createToken(user=user)
            job = cliSubHandler(currentItem, params, user, token)
            job = job.job
        return job

    cliHandler.subHandler = cliSubHandler
    cliHandler.getBatchParams = getBatchParams
    cliHandler.cliTitle = cliTitle
    if len(datalist):
        cliHandler.datalist = datalist
        for key, entry in datalist.items():

            datalistDesc = Description(clim.title)
            datalistDesc.__dict__ = handlerDesc.__dict__.copy()
            datalistDesc.notes('List values for %s' % key) \
                .produces('text/plain')
            datalistDesc._params = [
                param for param in datalistDesc._params
                if param['name'] not in entry['json']
                and param['name'] not in {k + FOLDER_SUFFIX for k in entry['json']}]

            @access.user
            @describeRoute(datalistDesc)
            def datalistHandler(resource, params):
                user = resource.getCurrentUser()
                currentItem = CLIItem.find(itemId, user)
                if not currentItem:
                    raise RestException('Invalid CLI Item id (%s).' % (itemId))
                token = Token().createToken(user=user)
                job = cliSubHandler(
                    currentItem, params, user, token, entry['json']).job  # noqa: B023
                delay = 0.01
                while job['status'] not in {JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED}:
                    time.sleep(delay)
                    delay = min(delay * 1.5, 1.0)
                    job = Job().load(id=job['_id'], force=True, includeLog=True)
                result = ''.join(job['log']) if 'log' in job else ''
                if '<element' in result:
                    result = result[result.index('<element'):]
                if '</element>' in result:
                    result = result[:result.rindex('</element>') + 10]
                return result

            entry['handler'] = datalistHandler
    return cliHandler


def genHandlerToReRunDockerCLI(cliItem, cliHandler):
    itemId = cliItem._id
    description = copy.deepcopy(cliHandler.description)
    for param in description.params:
        param['required'] = False
        param.pop('default', None)
    description.param('jobId', 'The previous job ID')
    description._params = description._params[-1:] + description._params[:-1]
    description._summary = 'Rerun ' + description._summary
    if description._notes:
        description._notes = 'Rerun a previous job: ' + description._notes

    @access.user
    @describeRoute(description)
    def rerunHandler(resource, params):
        user = resource.getCurrentUser()
        currentItem = CLIItem.find(itemId, user)
        if not currentItem:
            raise RestException('Invalid CLI Item id (%s).' % (itemId))
        originalJob = Job().load(params.pop('jobId'), user=user, level=AccessType.READ)
        newParams = originalJob.get('_original_params', {})
        originalName = originalJob.get('_original_name')
        originalPath = originalJob.get('_original_path')
        if ((originalName and cliItem.name != originalName)
                or (originalPath and cliItem.restBasePath != originalPath)):
            raise RestException('Original job was from %s/%s, not %s/%s.' % (
                originalPath or cliItem.restBasePath,
                originalName or cliItem.name, cliItem.restBasePath,
                cliItem.name))
        newParams.update(params)
        batchParams = cliHandler.getBatchParams(newParams)
        if len(batchParams):
            job = batchCLIJob(currentItem, newParams, user, cliHandler.cliTitle)
        else:
            token = Token().createToken(user=user)
            job = cliHandler.subHandler(currentItem, newParams, user, token)
            job = job.job
        return job

    return rerunHandler


def genRESTEndPointsForSlicerCLIsForItem(restResource, cliItem, registerNamedRoute=False):
    """Generates REST end points for slicer CLIs placed in subdirectories of a
    given root directory and attaches them to a REST resource with the given
    name.

    For each CLI, it creates:
    * a GET Route (<apiURL>/`restResourceName`/<cliRelativePath>/xml)
    that returns the xml spec of the CLI
    * a POST Route (<apiURL>/`restResourceName`/<cliRelativePath>/run)
    that runs the CLI

    It also creates a GET route (<apiURL>/`restResourceName`) that returns a
    list of relative routes to all CLIs attached to the generated REST resource

    Parameters
    ----------
    restResource : a dockerResource
        REST resource to which the end-points should be attached
    cliItem : CliItem
    """
    # validate restResource argument
    if not isinstance(restResource, Resource):
        raise Exception('restResource must be a Docker Resource')

    try:
        handler = genHandlerToRunDockerCLI(cliItem)
        rerunHandler = genHandlerToReRunDockerCLI(cliItem, handler)

        # define CLI handler function
        cliRunHandler = boundHandler(restResource)(handler)
        cliReRunHandler = boundHandler(restResource)(rerunHandler)

        cliRunHandlerName = 'run_%s' % cliItem._id
        cliReRunHandlerName = 'rerun_%s' % cliItem._id

        restRunPath = ('cli', str(cliItem._id), 'run')
        routes = [('POST', restRunPath, cliRunHandler, cliRunHandlerName)]
        restReRunPath = ('cli', str(cliItem._id), 'rerun')
        routes.append(('POST', restReRunPath, cliReRunHandler, cliReRunHandlerName))
        if registerNamedRoute:
            restNamedRunPath = (cliItem.restBasePath, cliItem.name, 'run')
            routes.append(('POST', restNamedRunPath, cliRunHandler, cliRunHandlerName))
            restNamedReRunPath = (cliItem.restBasePath, cliItem.name, 'rerun')
            routes.append(('POST', restNamedReRunPath, cliReRunHandler, cliReRunHandlerName))

        if hasattr(handler, 'datalist'):
            for key, entry in handler.datalist.items():
                dlHandler = boundHandler(restResource)(entry['handler'])
                dlHandlerName = 'dl_%s_%s' % (cliItem._id, key)
                dlHandlerPath = ('cli', str(cliItem._id), 'datalist', key)
                routes.append(('POST', dlHandlerPath, dlHandler, dlHandlerName))
                if registerNamedRoute:
                    dlHandlerPath = (cliItem.restBasePath, cliItem.name, 'datalist', key)
                    routes.append(('POST', dlHandlerPath, dlHandler, dlHandlerName))

        for routeMethod, routeName, routeHandler, routeHandlerName in routes:
            setattr(restResource, routeHandlerName, routeHandler)
            restResource.route(routeMethod, routeName, routeHandler)

        def undoFunction():
            try:
                for routeMethod, routeName, routeHandler, routeHandlerName in routes:
                    restResource.removeRoute(routeMethod, routeName, routeHandler)
                    if hasattr(restResource, routeHandlerName):
                        delattr(restResource, routeHandlerName)
            except Exception:
                logger.exception('Failed to remove route')

        # store new rest endpoint
        restResource.storeEndpoints(cliItem.image, cliItem.name, undoFunction)

        logger.debug('Created REST endpoints for %s', cliItem.name)
    except Exception:
        logger.exception('Failed to create REST endpoints for %r',
                         cliItem.name)

    return restResource
