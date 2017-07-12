from girder_worker.describe import get_registered_function

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
        func = get_registered_function(taskName)
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
    try:
        func = get_registered_function(taskName)
    except KeyError:
        raise RestException('Unknown task "%s"' % taskName)

    return func.call_item_task(inputs, outputs)
