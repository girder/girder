import six

from girder import events
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import ensureTokenScopes, filtermodel, loadmodel, Resource
from girder.constants import AccessType, TokenScope
from girder.models.model_base import ValidationException
from girder.plugins.worker import utils
from . import constants


class ItemTask(Resource):
    def __init__(self):
        super(ItemTask, self).__init__()

        self.resourceName = 'item_task'

        self.route('GET', (), self.listTasks)
        self.route('POST', (':id', 'execution'), self.executeTask)

    @access.public
    @describeRoute(
        Description('List all available tasks that can be executed.')
        .pagingParams(defaultSort='name')
    )
    @filtermodel(model='item')
    def listTasks(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')

        cursor = self.model('item').find({
            'meta.itemTaskSpec': {'$exists': True}
        }, sort=sort)

        return list(self.model('item').filterResultsByPermission(
            cursor, self.getCurrentUser(), level=AccessType.READ, limit=limit, offset=offset,
            flags=constants.ACCESS_FLAG_EXECUTE_TASK))

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
                    'mode': v['mode'],
                    'data': v['data'],
                    'type': 'none',
                    'format': 'none'
                }
            else:
                raise ValidationException('Invalid input mode: %s.' % v['mode'])

        return transformed

    def _transformOutputs(self, outputs, token):
        """
        Validates and sanitizes the input bindings. If they are Girder inputs, adds
        the necessary token info. If the token does not allow DATA_WRITE, or if the user
        does not have write access to the destination, raises an AccessException.
        """
        transformed = {}
        for k, v in six.viewitems(outputs):
            if v['mode'] == 'girder':
                ensureTokenScopes(token, TokenScope.DATA_WRITE)
                ptype = v.get('parent_type', 'folder')
                if ptype not in {'item', 'folder'}:
                    raise ValidationException('Invalid output parent type: %s.' % ptype)

                parent = self.model(ptype).load(
                    v['parent_id'], level=AccessType.WRITE, user=self.getCurrentUser(), exc=True)

                transformed[k] = utils.girderOutputSpec(
                    parent, parentType=ptype, token=token, name=v.get('name'), dataFormat='none')
            else:
                raise ValidationException('Invalid output mode: %s.' % v['mode'])

        return transformed


    @access.user(scope=constants.TOKEN_SCOPE_EXECUTE_TASK)
    @loadmodel(
        model='item', level=AccessType.READ, requiredFlags=constants.ACCESS_FLAG_EXECUTE_TASK)
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Execute a task described by an item.')
        .param('id', 'The ID of the item representing the task specification.', paramType='path')
        .param('jobTitle', 'Title for this job execution.', required=False)
        .param('inputs', 'The input bindings for the task.', required=False)
        .param('outputs', 'The output bindings for the task.', required=False)
        .param('includeJobInfo', 'Whether to track the task using a job record.', required=False,
               dataType='boolean', default=True)
    )
    def executeTask(self, item, params):
        includeJobInfo = self.boolParam('includeJobInfo', params, default=True)
        title = params.get('jobTitle', item['name'])
        task, handler = self._validateTask(item)

        jobModel = self.model('job', 'jobs')

        job = jobModel.createJob(
            title=title, type='item_task', handler=handler, user=self.getCurrentUser())

        # If this is a user auth token, we make an IO-enabled token
        token = self.getCurrentToken()
        if self.model('token').hasScope(token, TokenScope.USER_AUTH):
            token = self.model('token').createToken(
                user=self.getCurrentUser(), days=7, scope=(
                    TokenScope.DATA_READ, TokenScope.DATA_WRITE))
            job['itemTaskTempToken'] = token['_id']

        inputs = self.getParamJson('inputs', params, default={})
        outputs = self.getParamJson('outputs', params, default={})

        job['itemTaskId'] = item['_id']
        job['itemTaskBindings'] = {
            'inputs': inputs,
            'outputs': outputs
        }

        job['kwargs'] = {
            'task': task,
            'inputs': self._transformInputs(inputs, token),
            'outputs': self._transformOutputs(outputs, token),
            'validate': False,
            'auto_convert': False,
            'cleanup': True
        }

        if includeJobInfo:
            job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        return job
