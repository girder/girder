from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler, filtermodel
from girder.constants import AccessType
from girder.plugins.worker import utils
from . import constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@filtermodel(model='job', plugin='jobs')
@boundHandler()
@autoDescribeRoute(
    Description('Create item task specs based on a docker image.')
    .notes('This operates on an existing folder, adding item tasks '
           'using introspection of a docker image.')
    .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                model='folder', level=AccessType.WRITE)
    .param('image', 'The docker image name.', required=True, strip=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. '
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
                    'url': '/'.join((utils.getWorkerApiUrl(), 'item_task', str(folder['_id']),
                                     'json_specs')),
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
@boundHandler()
@autoDescribeRoute(
    Description('Create item tasks under a folder using a list of JSON specifications.')
    .modelParam('id', model='folder', force=True)
    .jsonParam('json', 'The JSON specifications as a list or a single object.',
               paramType='body')
    .param('image', 'The docker image name.', required=True, strip=True)
    .param('pullImage', 'Whether the image should be pulled from Docker Hub. ' +
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

        item = self.model('item').createItem(
            name=name,
            creator=user,
            folder=folder,
            description=itemTaskSpec.get('description', ''),
            reuseExisting=True)

        itemTaskSpec['docker_image'] = image
        itemTaskSpec['pull_image'] = pullImage
        self.model('item').setMetadata(item, {
            'itemTaskSpec': itemTaskSpec,
            'isItemTask': True
        })
