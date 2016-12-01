from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import filtermodel, loadmodel, Resource
from girder.constants import AccessType
from girder.models.model_base import ValidationException
from girder.plugins.worker import utils
from . import constants


class WorkerTask(Resource):
    def __init__(self):
        super(WorkerTask, self).__init__()

        self.resourceName = 'worker_task'

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
            'meta.workerTaskSpec': {'$exists': True}
        }, sort=sort)

        return list(self.model('item').filterResultsByPermission(
            cursor, self.getCurrentUser(), level=AccessType.READ, limit=limit, offset=offset))

    def _validateTask(self, item):
        """
        Some basic validation of the task spec.
        """
        if 'workerTaskSpec' not in item.get('meta'):
            raise ValidationException('Item (%s) does not contain a worker task specification.')
        spec = item['meta']['workerTaskSpec']

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

        return spec

    @access.token(scope=constants.TOKEN_SCOPE_EXECUTE_TASK)
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
        task = self._validateTask(item)

        jobModel = self.model('job', 'jobs')

        job = jobModel.createJob(
            title=title, type='worker_task', handler='worker_handler', user=self.getCurrentUser())


        job['workerTaskItemId'] = item['_id']
        job['kwargs'] = {
            'task': task,
            'inputs': self.getParamJson('inputs', params, default=[]),
            'outputs': self.getParamJson('outputs', params, default=[]),
            'validate': False,
            'auto_convert': False,
            'cleanup': True
        }

        if includeJobInfo:
            job['kwargs']['jobInfo'] = utils.jobInfoSpec(job)

        job = jobModel.save('job')
        jobModel.scheduleJob(job)

        return job
