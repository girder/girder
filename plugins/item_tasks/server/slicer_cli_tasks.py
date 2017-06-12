from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler, filtermodel, RestException
from girder.constants import AccessType
from girder.plugins.worker import utils
from . import cli_parser, constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model='job', plugin='jobs')
@boundHandler()
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
    .param('pullImage', 'Whether the image should be pulled from a docker registry. '
           'Set to false to use local images only.', dataType='boolean', required=False,
           default=True)
)
def runSlicerCliDescription(
        self, item, image, args, setName, setDescription, pullImage, params):
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
                'pull_image': pullImage,
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
                    'url': '/'.join((utils.getWorkerApiUrl(), 'item_task', str(item['_id']),
                                     'slicer_cli_xml')),
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
@boundHandler()
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
