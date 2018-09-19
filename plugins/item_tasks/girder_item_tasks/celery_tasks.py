import six

from girder_worker.app import app
from girder_worker.entrypoint import import_all_includes, get_extension_tasks, get_extensions
from girder_worker_utils import decorators

from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import boundHandler, RestException
from girder.constants import AccessType
from . import constants


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@boundHandler()
@autoDescribeRoute(
    Description('List girder_worker extensions installed on the server.')
)
def listGirderWorkerExtensions(self):
    return sorted(get_extensions())


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
    import_all_includes()
    func = app.tasks.get(taskName)
    if not func:
        raise RestException('Unknown task "%s"' % taskName)
    return describeItemTaskFromFunction(func, item, taskName, setName, setDescription)


@access.admin(scope=constants.TOKEN_SCOPE_AUTO_CREATE_CLI)
@boundHandler
@autoDescribeRoute(
    Description('Create item task specs for every function in a module.')
    .notes('This operates on an existing folder, adding item tasks '
           'for every function decorated with girder_worker.describe '
           'decorators.')
    .modelParam('id', 'The ID of the folder that the task specs will be added to.',
                model='folder', level=AccessType.WRITE)
    .param('extension', 'A girder_worker entry_point name containing tasks',
           required=True, strip=True)
)
def celeryTaskDescriptionForFolder(self, folder, extension, params):
    import_all_includes()
    try:
        tasks = get_extension_tasks(extension, celery_only=True)
    except KeyError:
        raise RestException('Unknown girder_worker extension')

    user = self.getCurrentUser()
    itemModel = self.model('item')
    items = []
    for name, func in six.iteritems(tasks):
        desc = decorators.describe_function(func)
        item = itemModel.createItem(
            name=desc['name'],
            creator=user,
            folder=folder,
            description=desc.get('description', ''),
            reuseExisting=True
        )

        items.append(describeItemTaskFromFunction(func, item, name))
    return items


@boundHandler
def describeItemTaskFromFunction(self, func, item, importName, setName=True, setDescription=True):
    try:
        description = decorators.describe_function(func)
    except Exception:
        raise RestException('Could not get a task description')

    item = self.model('item').setMetadata(item, {
        'isItemTask': True,
        'itemTaskName': description['name'],
        'itemTaskSpec': description,
        'itemTaskImport': importName
    })

    if setName:
        item['name'] = description['name']

    if setDescription:
        item['description'] = description.get('description', '')

    if setName or setDescription:
        self.model('item').save(item)

    return item


def runCeleryTask(taskName, inputs, outputs={}):
    import_all_includes()
    tasks = app.tasks

    if taskName not in tasks:
        raise RestException('Unknown task "%s"' % taskName)

    task = tasks[taskName]
    try:
        decorators.describe_function(task.run)
    except decorators.MissingDescriptionException:
        raise RestException('"%s" is not a girder_worker decorated task' % taskName)

    try:
        args, kwargs = decorators.parse_inputs(task.run, inputs)
    except decorators.MissingInputException as e:
        raise RestException(str(e))

    try:
        result = task.apply_async(args=args, kwargs=kwargs,
                                  girder_job_title=taskName)
    except Exception as e:
        raise RestException(str(e))

    return result.job
