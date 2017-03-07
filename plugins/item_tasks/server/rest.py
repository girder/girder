import json
import six

from girder import events
from girder import logger
from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import ensureTokenScopes, filtermodel, Resource, RestException, getApiUrl
from girder.constants import AccessType, TokenScope
from girder.models.model_base import ValidationException
from girder.plugins.worker import utils
from . import cli_parser, constants


class ItemTask(Resource):
    def __init__(self):
        super(ItemTask, self).__init__()

        self.resourceName = 'item_task'

        self.route('GET', (), self.listTasks)
        self.route('POST', (':id', 'execution'), self.executeTask)
        self.route('POST', (':id', 'slicer_cli_description'), self.runSlicerCliDescription)
        self.route('PUT', (':id', 'slicer_cli_xml'), self.setSpecFromXml)
        self.route('POST', (':id', 'json_description'), self.runJsonTasksDescription)
        self.route('POST', (':id', 'json_specs'), self.addJsonSpecs)

    @access.public
    @autoDescribeRoute(
        Description('List all available tasks that can be executed.')
        .pagingParams(defaultSort='name')
    )
    @filtermodel(model='item')
    def listTasks(self, limit, offset, sort, params):
        cursor = self.model('item').find({
            'meta.isItemTask': {'$exists': True}
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
                    'mode': 'inline',
                    'data': v['data']
                }
            else:
                raise ValidationException('Invalid input mode: %s.' % v['mode'])

        return transformed

    def _transformOutputs(self, outputs, token, job):
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
                if ptype not in {'item', 'folder'}:
                    raise ValidationException('Invalid output parent type: %s.' % ptype)

                parent = self.model(ptype).load(
                    v['parent_id'], level=AccessType.WRITE, user=self.getCurrentUser(), exc=True)

                transformed[k] = utils.girderOutputSpec(
                    parent, parentType=ptype, token=token, name=v.get('name'), dataFormat='none',
                    reference=json.dumps({
                        'type': 'item_tasks.output',
                        'id': k,
                        'jobId': str(job['_id'])
                    }))
            else:
                raise ValidationException('Invalid output mode: %s.' % v['mode'])

        return transformed

    @access.user(scope=constants.TOKEN_SCOPE_EXECUTE_TASK)
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Execute a task described by an item.')
        .modelParam('id', 'The ID of the item representing the task specification.', model='item',
                    level=AccessType.READ, requiredFlags=constants.ACCESS_FLAG_EXECUTE_TASK)
        .param('jobTitle', 'Title for this job execution.', required=False)
        .param('includeJobInfo', 'Whether to track the task using a job record.',
               required=False, dataType='boolean', default=True)
        .jsonParam('inputs', 'The input bindings for the task.', required=False,
                   requireObject=True)
        .jsonParam('outputs', 'The output bindings for the task.', required=False,
                   requireObject=True)
    )
    def executeTask(self, item, jobTitle, includeJobInfo, inputs, outputs, params):
        user = self.getCurrentUser()
        if jobTitle is None:
            jobTitle = item['name']
        task, handler = self._validateTask(item)

        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title=jobTitle, type='item_task', handler=handler, user=user)

        # If this is a user auth token, we make an IO-enabled token
        token = self.getCurrentToken()
        tokenModel = self.model('token')
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
                'outputs': self._transformOutputs(outputs, token, job),
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

    @access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Create an item task spec based on a docker image.')
        .notes('This operates on an existing item, turning it into an item task '
               'using Slicer CLI introspection of a docker image.')
        .modelParam('id', 'The ID of the item that the task spec will be bound to.',
                    model='item', level=AccessType.WRITE)
        .param('image', 'The docker image name. If not passed, uses the existing'
               'itemTaskSpec.docker_image metadata value.', required=False, strip=True)
        .jsonParam('args', 'Arguments to be passed to the docker container to output the '
                   'Slicer CLI spec.', required=False, default=[], requireArray=True)
        .param('setName', 'Whether item name should be changed to the title of the CLI.',
               dataType='boolean', required=False, default=True)
        .param('setDescription', 'Whether the item description should be changed to the '
               'description of the CLI.', dataType='boolean', required=False, default=True)
    )
    def runSlicerCliDescription(self, item, image, args, setName, setDescription, params):
        if 'meta' not in item:
            item['meta'] = {}

        if image is None:
            image = item.get('meta', {}).get('itemTaskSpec', {}).get('docker_image')

        if not image:
            raise RestException(
                'You must pass an image parameter, or set the itemTaskSpec.docker_image '
                'field of the item.')

        jobModel = self.model('job', 'jobs')
        token = self.model('token').createToken(
            days=3, scope='item_task.set_task_spec.%s' % item['_id'])
        job = jobModel.createJob(
            title='Read docker Slicer CLI: %s' % image, type='item_task.slicer_cli',
            handler='worker_handler', user=self.getCurrentUser())

        if args[-1:] == ['--xml']:
            args = args[:-1]

        job.update({
            'itemTaskId': item['_id'],
            'kwargs': {
                'task': {
                    'mode': 'docker',
                    'docker_image': image,
                    'container_args': args + ['--xml'],
                    'outputs': [{
                        'id': '_stdout',
                        'format': 'text'
                    }],
                },
                'outputs': {
                    '_stdout': {
                        'mode': 'http',
                        'method': 'PUT',
                        'format': 'text',
                        'url': '/'.join((getApiUrl(), self.resourceName,
                                         str(item['_id']), 'slicer_cli_xml')),
                        'params': {
                            'setName': setName,
                            'setDescription': setDescription
                        },
                        'headers': {'Girder-Token': token['_id']}
                    }
                },
                'jobInfo': utils.jobInfoSpec(job),
                'validate': False,
                'auto_convert': False,
                'cleanup': True
            }
        })

        item['meta']['itemTaskSpec'] = {
            'mode': 'docker',
            'docker_image': image
        }

        if args:
            item['meta']['itemTaskSlicerCliArgs'] = args

        self.model('item').save(item)

        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @autoDescribeRoute(
        Description('Set a task spec on an item from a Slicer CLI XML spec.')
        .modelParam('id', model='item', force=True)
        .param('xml', 'The Slicer CLI XML spec.', paramType='body')
        .param('setName', 'Whether item name should be changed to the title of the CLI.',
               dataType='boolean', required=True)
        .param('setDescription', 'Whether the item description should be changed to the '
               'description of the CLI.', dataType='boolean', required=False, default=True),
        hide=True
    )
    def setSpecFromXml(self, item, xml, setName, setDescription, params):
        self.ensureTokenScopes('item_task.set_task_spec.%s' % item['_id'])

        args = item.get('meta', {}).get('itemTaskSlicerCliArgs') or []
        cliSpec = cli_parser.parseSlicerCliXml(xml)

        itemTaskSpec = item.get('meta', {}).get('itemTaskSpec', {})
        itemTaskSpec.update({
            'container_args': args + cliSpec['args'],
            'inputs': cliSpec['inputs'],
            'outputs': cliSpec['outputs']
        })

        if setName:
            item['name'] = cliSpec['title']
        if setDescription:
            item['description'] = cliSpec['description']

        self.model('item').setMetadata(item, {
            'itemTaskSpec': itemTaskSpec,
            'isItemTask': True
        })

    @access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
    @filtermodel(model='job', plugin='jobs')
    @autoDescribeRoute(
        Description('Create item task specs based on a docker image.')
        .notes('This operates on an existing folder, adding item tasks '
               'using introspection of a docker image.')
        .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                    model='folder', level=AccessType.WRITE)
        .param('image', 'The docker image name.', required=True, strip=True)
        .param('pullImage', 'Whether the image should be pulled from a docker registry. ' +
               'Set to false to use local images only.',
               dataType='boolean', required=False, default=True)
    )
    def runJsonTasksDescription(self, folder, image, pullImage, params):
        jobModel = self.model('job', 'jobs')
        token = self.model('token').createToken(
            days=3, scope='item_task.set_task_spec.%s' % folder['_id'],
            user=self.getCurrentUser())
        job = jobModel.createJob(
            title='Read docker task specs: %s' % image, type='item_task.json_description',
            handler='worker_handler', user=self.getCurrentUser())

        jobOptions = {
            'itemTaskId': folder['_id'],
            'kwargs': {
                'task': {
                    'mode': 'docker',
                    'docker_image': image,
                    'container_args': [],
                    'pull_image': pullImage,
                    'outputs': [{
                        'id': '_stdout',
                        'format': 'text'
                    }],
                },
                'outputs': {
                    '_stdout': {
                        'mode': 'http',
                        'method': 'POST',
                        'format': 'text',
                        'url': '/'.join((getApiUrl(), self.resourceName,
                                         str(folder['_id']), 'json_specs')),
                        'headers': {'Girder-Token': token['_id']},
                        'params': {
                            'image': image,
                            'pullImage': pullImage
                        }
                    }
                },
                'jobInfo': utils.jobInfoSpec(job),
                'validate': False,
                'auto_convert': False,
                'cleanup': True
            }
        }
        job.update(jobOptions)

        job = jobModel.save(job)
        jobModel.scheduleJob(job)
        return job

    @access.token
    @autoDescribeRoute(
        Description('Create item tasks under a folder using a list of JSON specifications.')
        .modelParam('id', model='folder', force=True)
        .jsonParam('json', 'The JSON specifications as a list or a single specification object.', paramType='body')
        .param('image', 'The docker image name.', required=True, strip=True)
        .param('pullImage', 'Whether the image should be pulled from a docker registry. ' +
               'Set to false to use local images only.',
               dataType='boolean', required=False, default=True),
        hide=True
    )
    def addJsonSpecs(self, folder, json, image, pullImage, params):
        self.ensureTokenScopes('item_task.set_task_spec.%s' % folder['_id'])
        token = self.getCurrentToken()
        user = self.model('user').load(token['userId'], force=True)

        if not isinstance(json, list):
            json = [json]

        for itemIndex, itemTaskSpec in enumerate(json):
            name = itemTaskSpec.get('name')
            if not name:
                name = image
                if len(json) > 1:
                    name += ' ' + str(itemIndex)

            logger.info('Configuring item "%s"' % name)

            item = self.model('item').createItem(
                name=name,
                creator=user,
                folder=folder,
                description=itemTaskSpec.get('description', ''),
                reuseExisting=True)
            logger.info(pullImage)
            logger.info(params)
            itemTaskSpec['docker_image'] = image
            itemTaskSpec['pull_image'] = pullImage
            self.model('item').setMetadata(item, {
                'itemTaskSpec': itemTaskSpec,
                'isItemTask': True
            })
