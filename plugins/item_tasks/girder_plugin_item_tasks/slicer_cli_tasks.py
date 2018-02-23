import json

from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler, filtermodel
from girder.constants import AccessType
from girder.exceptions import RestException
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.token import Token
from girder.models.user import User
from girder_plugin_jobs.models.job import Job
from girder_plugin_worker import utils
from . import cli_parser, constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model=Job)
@boundHandler
@autoDescribeRoute(
    Description('Create an item task spec based on a docker image.')
    .notes('This operates on an existing item, turning it into an item task '
           'using Slicer CLI introspection of a docker image.')
    .modelParam('id', 'The ID of the item that the task spec will be bound to.',
                model=Item, level=AccessType.WRITE)
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
    .deprecated()
)
def runSlicerCliTasksDescriptionForItem(
        self, item, image, args, setName, setDescription, pullImage, params):
    if 'meta' not in item:
        item['meta'] = {}

    if image is None:
        image = item.get('meta', {}).get('itemTaskSpec', {}).get('docker_image')

    if not image:
        raise RestException(
            'You must pass an image parameter, or set the itemTaskSpec.docker_image '
            'field of the item.')

    jobModel = Job()
    token = Token().createToken(
        days=3, scope='item_task.set_task_spec.%s' % item['_id'])
    job = jobModel.createJob(
        title='Read docker Slicer CLI: %s' % image, type='item.item_task_slicer_cli_description',
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
                    'url': '/'.join((utils.getWorkerApiUrl(), 'item', str(item['_id']),
                                     'item_task_slicer_cli_xml')),
                    'params': {
                        'setName': setName,
                        'setDescription': setDescription
                    },
                    'headers': {'Girder-Token': token['_id']}
                }
            },
            'jobInfo': utils.jobInfoSpec(job),
            'validate': False,
            'auto_convert': False
        }
    })

    item['meta']['itemTaskSpec'] = {
        'mode': 'docker',
        'docker_image': image
    }

    if args:
        item['meta']['itemTaskSlicerCliArgs'] = args

    Item().save(item)

    job = jobModel.save(job)
    jobModel.scheduleJob(job)

    return job


@access.token
@boundHandler
@autoDescribeRoute(
    Description('Set a task spec on an item from a Slicer CLI XML spec.')
    .modelParam('id', model=Item, force=True)
    .param('xml', 'The Slicer CLI XML spec.', paramType='body')
    .param('setName', 'Whether item name should be changed to the title of the CLI.',
           dataType='boolean', required=True)
    .param('setDescription', 'Whether the item description should be changed to the '
           'description of the CLI.', dataType='boolean', required=False, default=True)
    .deprecated(),
    hide=True
)
def configureItemTaskFromSlicerCliXml(self, item, xml, setName, setDescription, params):
    Token().requireScope(self.getCurrentToken(), 'item_task.set_task_spec.%s' % item['_id'])

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

    Item().setMetadata(item, {
        'itemTaskSpec': itemTaskSpec,
        'isItemTask': True
    })


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model=Job)
@boundHandler
@autoDescribeRoute(
    Description('Create item task specs based on a docker image.')
    .notes('This operates on an existing folder, adding item tasks '
           'using Slicer CLI introspection of a docker image.')
    .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                model=Folder, level=AccessType.WRITE)
    .param('image', 'The docker image name.', required=True, strip=True)
    .jsonParam('args', 'Arguments to be passed to the docker container to output the '
               'Slicer CLI spec.', required=False, default=[], requireArray=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True)
)
def runSlicerCliTasksDescriptionForFolder(self, folder, image, args, pullImage, params):
    jobModel = Job()
    token = Token().createToken(
        days=3, scope='item_task.set_task_spec.%s' % folder['_id'], user=self.getCurrentUser())
    job = jobModel.createJob(
        title='Read docker task specs: %s' % image, type='folder.item_task_slicer_cli_description',
        handler='worker_handler', user=self.getCurrentUser())

    if args[-1:] == ['--xml']:
        args = args[:-1]

    jobOptions = {
        'itemTaskId': folder['_id'],
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
                    'method': 'POST',
                    'format': 'text',
                    'url': '/'.join((utils.getWorkerApiUrl(), 'folder', str(folder['_id']),
                                     'item_task_slicer_cli_xml')),
                    'headers': {'Girder-Token': token['_id']},
                    'params': {
                        'image': image,
                        'args': json.dumps(args),
                        'pullImage': pullImage
                    }
                }
            },
            'jobInfo': utils.jobInfoSpec(job),
            'validate': False,
            'auto_convert': False
        }
    }
    job.update(jobOptions)

    job = jobModel.save(job)
    jobModel.scheduleJob(job)
    return job


@access.token
@boundHandler
@autoDescribeRoute(
    Description('Create item tasks under a folder using a list of Slicer CLI XML specs.')
    .modelParam('id', model=Folder, force=True)
    .param('xml', 'The Slicer CLI XML spec.', paramType='body')
    .param('image', 'The docker image name.', required=True, strip=True)
    .jsonParam('args', 'Arguments to be passed to the docker container to output the '
               'Slicer CLI spec.', required=False, default=[], requireArray=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True),
    hide=True
)
def createItemTasksFromSlicerCliXml(self, folder, xml, image, args, pullImage, params):
    Token().requireScope(self.getCurrentToken(), 'item_task.set_task_spec.%s' % folder['_id'])
    token = self.getCurrentToken()
    user = User().load(token['userId'], force=True)

    # TODO: Update once CLI spec supports multiple executables
    cliSpec = cli_parser.parseSlicerCliXml(xml)

    itemTaskSpec = {
        'container_args': args + cliSpec['args'],
        'inputs': cliSpec['inputs'],
        'outputs': cliSpec['outputs']
    }

    item = Item().createItem(
        name=cliSpec['title'],
        creator=user,
        folder=folder,
        description=cliSpec['description'],
        reuseExisting=True)

    itemTaskSpec['mode'] = 'docker'
    itemTaskSpec['docker_image'] = image
    itemTaskSpec['pull_image'] = pullImage
    Item().setMetadata(item, {
        'itemTaskSlicerCliArgs': args,
        'itemTaskSpec': itemTaskSpec,
        'isItemTask': True
    })
