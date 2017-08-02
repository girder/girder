from girder_worker.app import app
from girder_worker import describe
from girder_worker.entrypoint import import_all_includes

from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler, RestException
from girder.constants import AccessType
from . import constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@boundHandler()
@autoDescribeRoute(
    Description('Create item task specs based on a celery task.')
    .notes('This operates on an existing item, adding item tasks '
           'using girder_worker.describe decorators.')
    .modelParam('id', 'The ID of the item that the task specs will be added to.',
                model='item', level=AccessType.WRITE)
    .param('taskName', 'The module path to the python function', required=True, strip=True)
    .param('setName', 'Whether item name should be changed to the title of the CLI.',
           dataType='boolean', required=False, default=True)
    .param('setDescription', 'Whether the item description should be changed to the '
           'description of the CLI.', dataType='boolean', required=False, default=True)
)
def describeCeleryTaskItem(self, item, taskName, setName, setDescription, params):
    try:
        func = describe.get_registered_function(taskName)
    except KeyError:
        raise RestException('Unknown task "%s"' % taskName)

    try:
        description = func.describe()
    except Exception:
        raise RestException('Could not get description for "%s"' % taskName)

    item = self.model('item').setMetadata(item, {
        'isItemTask': True,
        'itemTaskName': description['name'],
        'itemTaskSpec': description,
        'itemTaskImport': taskName
    })

    if setName:
        item['name'] = description['name']

    if setDescription:
        item['description'] = description['description']

    if setName or setDescription:
        self.model('item').save(item)

    return item


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@boundHandler
@autoDescribeRoute(
    Description('Create item task specs for every function in a module.')
    .notes('This operates on an existing folder, adding item tasks '
           'for every function decorated with girder_worker.describe '
           'decorators.')
    .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                model='folder', level=AccessType.WRITE)
    .param('module', 'A python module path containing task functions', required=True, strip=True)
)
def runJsonTasksDescriptionForFolder(self, folder, image, pullImage, params):
    pass


def runGirderWorkerTask(taskName, inputs, outputs={}):
    import_all_includes()
    tasks = app.tasks

    if taskName not in tasks:
        raise RestException('Unknown task "%s"' % taskName)

    task = tasks[taskName]
    try:
        describe.describe_function(task.run)
    except describe.MissingDescriptionException:
        raise RestException('"%s" is not a girder_worker decorated task' % taskName)

    try:
        args, kwargs = describe.parse_inputs(task.run, inputs)
    except describe.MissingInputException as e:
        raise RestException(str(e))

    try:
        result = task.delay(*args, **kwargs)
    except Exception as e:
        raise RestException(str(e))

    return result.job
