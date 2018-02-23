import json
import six

from girder import events
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import ensureTokenScopes, filtermodel, Resource
from girder.constants import AccessType, TokenScope
from girder.exceptions import ValidationException
from girder.models.item import Item
from girder.models.token import Token
from girder_plugin_jobs.models.job import Job
from girder_plugin_worker import utils
from . import constants
from .json_tasks import createItemTasksFromJson, runJsonTasksDescriptionForFolder
from .slicer_cli_tasks import configureItemTaskFromSlicerCliXml, runSlicerCliTasksDescriptionForItem
from .celery_tasks import runCeleryTask, listGirderWorkerExtensions


class ItemTask(Resource):
    def __init__(self):
        super(ItemTask, self).__init__()

        self.resourceName = 'item_task'

        self.route('GET', (), self.listTasks)
        self.route('POST', (':id', 'execution'), self.executeTask)
        self.route('GET', ('extensions',), listGirderWorkerExtensions)

        # Deprecated in favor of POST /item/:id/item_task_slicer_cli_description
        self.route('POST', (':id', 'slicer_cli_description'), runSlicerCliTasksDescriptionForItem)
        # Deprecated in favor of PUT /item/:id/item_task_slicer_cli_xml
        self.route('PUT', (':id', 'slicer_cli_xml'), configureItemTaskFromSlicerCliXml)
        # Deprecated in favor of POST /folder/:id/item_task_json_description
        self.route('POST', (':id', 'json_description'), runJsonTasksDescriptionForFolder)
        # Deprecated in favor of POST /folder/:id/:item_task_json_specs
        self.route('POST', (':id', 'json_specs'), createItemTasksFromJson)

    @access.public
    @autoDescribeRoute(
        Description('List all available tasks that can be executed.')
        .pagingParams(defaultSort='name')
        .param('minFileInputs', 'Filter tasks by minimum number of file inputs.', required=False,
               dataType='int')
        .param('maxFileInputs', 'Filter tasks by maximum number of file inputs.', required=False,
               dataType='int')
    )
    @filtermodel(model=Item)
    def listTasks(self, limit, offset, sort, minFileInputs, maxFileInputs, params):
        cursor = Item().find({
            'meta.isItemTask': {'$exists': True}
        }, sort=sort)

        if minFileInputs is not None or maxFileInputs is not None:
            cursor = self._filterMinMaxFileInputs(cursor, minFileInputs, maxFileInputs)

        return list(Item().filterResultsByPermission(
            cursor, self.getCurrentUser(), level=AccessType.READ, limit=limit, offset=offset,
            flags=constants.ACCESS_FLAG_EXECUTE_TASK))

    def _filterMinMaxFileInputs(self, cursor, minFileInputs, maxFileInputs):
        for item in cursor:
            fileCount = sum(
                input['type'] == 'file'
                for input in
                item['meta']['itemTaskSpec'].get('inputs', []))

            if minFileInputs is not None and fileCount < minFileInputs:
                continue
            elif maxFileInputs is not None and fileCount > maxFileInputs:
                continue
            else:
                yield item

    def _validateTask(self, item):
        """
        Some basic validation of the task spec.
        """
        if 'itemTaskSpec' not in item.get('meta'):
            raise ValidationException('Item (%s) does not contain an item task specification.')
        spec = item['meta']['itemTaskSpec']

        handler = item.get('meta', {}).get('itemTaskHandler') or 'worker_handler'

        event = events.trigger('item_tasks.handler.%s.validate' % handler, {
            'item': item,
            'spec': spec
        })

        if len(event.responses):
            spec = event.responses[-1]

        if event.defaultPrevented:
            return spec, handler

        if not isinstance(spec, dict):
            raise ValidationException('Task spec should be a JSON object.')

        inputs = spec.get('inputs', [])
        outputs = spec.get('outputs', [])

        if not isinstance(inputs, (list, tuple)):
            raise ValidationException('Task inputs must be a list.')

        if not isinstance(outputs, (list, tuple)):
            raise ValidationException('Task outputs must be a list.')

        if 'mode' not in spec:
            raise ValidationException('Task must contain a "mode" field.')

        # Ensure that format and type keys exist in every task IO spec,
        # the worker complains otherwise.
        for ioSpec in inputs + outputs:
            ioSpec['format'] = ioSpec.get('format', 'none')
            ioSpec['type'] = ioSpec.get('type', 'none')

        return spec, handler

    def _transformInputs(self, inputs, token):
        """
        Validates and sanitizes the input bindings. If they are Girder inputs, adds
        the necessary token info. If the token does not allow DATA_READ, or if the user
        does not have read access to the resource, raises an AccessException.
        """
        transformed = {}
        for k, v in six.viewitems(inputs):
            if v['mode'] == 'girder':
                ensureTokenScopes(token, TokenScope.DATA_READ)
                rtype = v.get('resource_type', 'file')
                if rtype not in {'file', 'item', 'folder'}:
                    raise ValidationException('Invalid input resource_type: %s.' % rtype)

                resource = self.model(rtype).load(
                    v['id'], level=AccessType.READ, user=self.getCurrentUser(), exc=True)

                transformed[k] = utils.girderInputSpec(
                    resource, resourceType=rtype, token=token, dataFormat='none')
            elif v['mode'] == 'inline':
                transformed[k] = {
                    'mode': 'inline',
                    'data': v['data']
                }
            else:
                raise ValidationException('Invalid input mode: %s.' % v['mode'])

        return transformed

    def _transformOutputs(self, outputs, token, job, task, taskId):
        """
        Validates and sanitizes the output bindings. If they are Girder outputs, adds
        the necessary token info. If the token does not allow DATA_WRITE, or if the user
        does not have write access to the destination, raises an AccessException.
        """
        transformed = {}
        for k, v in six.viewitems(outputs):
            if v['mode'] == 'girder':
                ensureTokenScopes(token, TokenScope.DATA_WRITE)
                ptype = v.get('parent_type', 'folder')
                if not self._validateOutputParentType(k, ptype, task['outputs']):
                    raise ValidationException('Invalid output parent type: %s.' % ptype)

                parent = self.model(ptype).load(
                    v['parent_id'], level=AccessType.WRITE, user=self.getCurrentUser(), exc=True)

                transformed[k] = utils.girderOutputSpec(
                    parent, parentType=ptype, token=token, name=v.get('name'), dataFormat='none',
                    reference=json.dumps({
                        'type': 'item_tasks.output',
                        'id': k,
                        'jobId': str(job['_id']),
                        'taskId': str(taskId)
                    }))
            else:
                raise ValidationException('Invalid output mode: %s.' % v['mode'])

        return transformed

    def _validateOutputParentType(self, outputId, parentType, outputSpec):
        """
        Checks if the output parent type is compatible with the output type.
        """

        # Find the corresponding output specification for the given outputID
        for output in outputSpec:
            if outputId == output['id']:
                # If a corresponding output is found, check if its parent type is valid
                if output['type'] == 'new-file' and parentType not in {'item', 'folder'}:
                    return False
                elif output['type'] == 'new-folder' and\
                        parentType not in {'folder', 'user', 'collection'}:
                    return False
                else:
                    return True
        else:
            raise ValidationException('Invalid output id: %s.' % outputId)

    @access.user(scope=constants.TOKEN_SCOPE_EXECUTE_TASK)
    @filtermodel(model=Job)
    @autoDescribeRoute(
        Description('Execute a task described by an item.')
        .modelParam('id', 'The ID of the item representing the task specification.', model=Item,
                    level=AccessType.READ, requiredFlags=constants.ACCESS_FLAG_EXECUTE_TASK)
        .param('jobTitle', 'Title for this job execution.', required=False)
        .param('includeJobInfo', 'Whether to track the task using a job record.',
               required=False, dataType='boolean', default=True)
        .jsonParam('inputs', 'The input bindings for the task.', required=False,
                   requireObject=True)
        .jsonParam('outputs', 'The output bindings for the task.', required=False,
                   requireObject=True)
    )
    def executeTask(self, item, jobTitle, includeJobInfo, inputs, outputs):
        user = self.getCurrentUser()
        if jobTitle is None:
            jobTitle = item['name']
        task, handler = self._validateTask(item)

        if task.get('mode') == 'girder_worker':
            return runCeleryTask(item['meta']['itemTaskImport'], inputs)

        jobModel = self.model('job', 'jobs')
        jobModel = Job()
        job = jobModel.createJob(
            title=jobTitle, type='item_task', handler=handler, user=user)

        # If this is a user auth token, we make an IO-enabled token
        token = self.getCurrentToken()
        tokenModel = Token()
        if tokenModel.hasScope(token, TokenScope.USER_AUTH):
            token = tokenModel.createToken(
                user=user, days=7, scope=(TokenScope.DATA_READ, TokenScope.DATA_WRITE))
            job['itemTaskTempToken'] = token['_id']

        token = tokenModel.addScope(token, 'item_tasks.job_write:%s' % job['_id'])

        job.update({
            'itemTaskId': item['_id'],
            'itemTaskBindings': {
                'inputs': inputs,
                'outputs': outputs
            },
            'kwargs': {
                'task': task,
                'inputs': self._transformInputs(inputs, token),
                'outputs': self._transformOutputs(outputs, token, job, task, item['_id']),
                'validate': False,
                'auto_convert': False,
                'cleanup': True
            }
        })

        if includeJobInfo:
            job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        if 'itemTaskCeleryQueue' in item.get('meta', {}):
            job['celeryQueue'] = item['meta']['itemTaskCeleryQueue']

        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        return job
