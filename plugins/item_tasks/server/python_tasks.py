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
    Description('Create item task specs based on girder_worker task.')
    .notes('This operates on an existing item, adding item tasks '
           'using girder_worker.describe decorators.')
    .modelParam('id', 'The ID of the item that the task specs will be added to.',
                model='item', level=AccessType.WRITE)
    .param('taskName', 'The module path to the python function', required=True, strip=True)
)
def describeGWTaskItem(self, item, params):
    taskName = params['taskName']
    try:
        func = describe.get_registered_function(taskName)
    except KeyError:
        raise RestException('Unknown task "%s"' % taskName)

    try:
        description = func.describe()
    except Exception:
        raise RestException('Could not get description for "%s"' % taskName)

    self.model('item').setMetadata(item, {
        'isItemTask': True,
        'itemTaskName': description['name'],
        'itemTaskSpec': description,
        'itemTaskImport': taskName
    })


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
    except Exception:
        raise RestException(str(e))

    return result.job
