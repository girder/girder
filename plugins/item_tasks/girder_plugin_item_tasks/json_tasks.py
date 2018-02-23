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
from . import constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model=Job)
@boundHandler
@autoDescribeRoute(
    Description('Create item task spec based on a task in a docker image.')
    .notes('This operates on an existing item, turning it into an item task '
           'using introspection of a docker image.')
    .modelParam('id', 'The ID of the item that the task spec will be bound to.',
                model=Item, level=AccessType.WRITE)
    .param('image', 'The docker image name. If not passed, uses the existing'
           'itemTaskSpec.docker_image metadata value.', required=False, strip=True)
    .param('taskName', 'The task name.', required=True, strip=True)
    .param('setName', 'Whether item name should be changed to the title of the CLI.',
           dataType='boolean', required=False, default=True)
    .param('setDescription', 'Whether the item description should be changed to the '
           'description of the CLI.', dataType='boolean', required=False, default=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True)
)
def runJsonTasksDescriptionForItem(self, item, image, taskName, setName, setDescription,
                                   pullImage, params):
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
        days=3, scope='item_task.set_task_spec.%s' % item['_id'],
        user=self.getCurrentUser())
    job = jobModel.createJob(
        title='Read docker task specs: %s' % image, type='item.item_task_json_description',
        handler='worker_handler', user=self.getCurrentUser())

    jobOptions = {
        'itemTaskId': item['_id'],
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
                    'method': 'PUT',
                    'format': 'text',
                    'url': '/'.join((utils.getWorkerApiUrl(), 'item', str(item['_id']),
                                     'item_task_json_specs')),
                    'headers': {'Girder-Token': token['_id']},
                    'params': {
                        'image': image,
                        'taskName': taskName,
                        'setName': setName,
                        'setDescription': setDescription,
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
    Description('Set a task spec on an item from a JSON specification.')
    .modelParam('id', model=Item, force=True)
    .jsonParam('json', 'The JSON specifications as a list or a single object.',
               paramType='body')
    .param('image', 'The docker image name.', required=True, strip=True)
    .param('taskName', 'The task name.', required=True, strip=True)
    .param('setName', 'Whether item name should be changed to the name of the task.',
           dataType='boolean', required=False, default=True)
    .param('setDescription', 'Whether the item description should be changed to the '
           'description of the task.', dataType='boolean', required=False, default=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True),
    hide=True
)
def configureItemTaskFromJson(self, item, json, image, taskName, setName, setDescription,
                              pullImage):
    Token().requireScope(self.getCurrentToken(), 'item_task.set_task_spec.%s' % item['_id'])

    if not isinstance(json, list):
        json = [json]

    for itemIndex, itemTaskSpec in enumerate(json):
        specName = itemTaskSpec.get('name')
        if specName == taskName:
            if setName:
                item['name'] = taskName
            if setDescription:
                item['description'] = itemTaskSpec.get('description', '')

            itemTaskSpec['docker_image'] = image
            itemTaskSpec['pull_image'] = pullImage
            Item().setMetadata(item, {
                'itemTaskName': taskName,
                'itemTaskSpec': itemTaskSpec,
                'isItemTask': True
            })
            break
    else:
        raise RestException('Task with name "%s" not found in JSON specification' % taskName)


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model=Job)
@boundHandler
@autoDescribeRoute(
    Description('Create item task specs based on a docker image.')
    .notes('This operates on an existing folder, adding item tasks '
           'using introspection of a docker image.')
    .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                model=Folder, level=AccessType.WRITE)
    .param('image', 'The docker image name.', required=True, strip=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True)
    .deprecated()
)
def runJsonTasksDescriptionForFolder(self, folder, image, pullImage, params):
    jobModel = Job()
    token = Token().createToken(
        days=3, scope='item_task.set_task_spec.%s' % folder['_id'],
        user=self.getCurrentUser())
    job = jobModel.createJob(
        title='Read docker task specs: %s' % image, type='folder.item_task_json_description',
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
                    'url': '/'.join((utils.getWorkerApiUrl(), 'folder', str(folder['_id']),
                                     'item_task_json_specs')),
                    'headers': {'Girder-Token': token['_id']},
                    'params': {
                        'image': image,
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
    Description('Create item tasks under a folder using a list of JSON specifications.')
    .modelParam('id', model=Folder, force=True)
    .jsonParam('json', 'The JSON specifications as a list or a single object.',
               paramType='body')
    .param('image', 'The docker image name.', required=True, strip=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. ' +
           'Set to false to use local images only.',
           dataType='boolean', required=False, default=True)
    .deprecated(),
    hide=True
)
def createItemTasksFromJson(self, folder, json, image, pullImage, params):
    Token().requireScope(self.getCurrentToken(), 'item_task.set_task_spec.%s' % folder['_id'])
    token = self.getCurrentToken()
    user = User().load(token['userId'], force=True)

    if not isinstance(json, list):
        json = [json]

    for itemIndex, itemTaskSpec in enumerate(json):
        origName = itemTaskSpec.get('name')
        name = origName
        if not name:
            name = image
            if len(json) > 1:
                name += ' ' + str(itemIndex)

        item = Item().createItem(
            name=name,
            creator=user,
            folder=folder,
            description=itemTaskSpec.get('description', ''),
            reuseExisting=True)

        itemTaskSpec['docker_image'] = image
        itemTaskSpec['pull_image'] = pullImage
        Item().setMetadata(item, {
            'itemTaskName': origName or '',
            'itemTaskSpec': itemTaskSpec,
            'isItemTask': True
        })
