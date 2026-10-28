from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, boundHandler
from girder.constants import AccessType, SortDir, TokenScope
from girder.exceptions import RestException
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.user import User
from girder.utility import assetstore_utilities
from girder.utility import path as path_util

from . import tasks, utils
from .models import Checkout, CheckoutFile
from .settings import PluginSettings


def _checkPermission(user):
    if Setting().get(PluginSettings.ADMIN_ONLY) and not user.get('admin'):
        raise RestException('Only administrators may check out folders.', code=403)


def _ensureWorker():
    # Imported here to avoid a circular import through girder_worker's plugin
    # discovery when girder.tasks is first loaded
    from girder.tasks import ensure_local_worker_available

    ensure_local_worker_available()


def _requireAssetstore():
    assetstore = utils.getTargetAssetstore()
    if assetstore is None:
        raise RestException('No filesystem assetstore is configured for local checkouts.')
    return assetstore


@access.user(scope=TokenScope.DATA_READ)
@boundHandler
@autoDescribeRoute(
    Description('Get the local checkout status of a folder.')
    .modelParam('id', model=Folder, level=AccessType.READ)
    .param('details', 'Whether to count the files in the folder that can be or '
           'have been made local.  This can be slow for large folders.',
           dataType='boolean', default=True, required=False)
    .errorResponse('ID was invalid.')
    .errorResponse('Read access was denied for the folder.', 403)
)
def getFolderCheckout(self, folder, details):
    assetstore = utils.getTargetAssetstore()
    result = {
        'checkout': Checkout().findByFolder(folder),
        'enabled': assetstore is not None,
        'assetstoreName': assetstore['name'] if assetstore else None,
        'maxDays': Setting().get(PluginSettings.MAX_DAYS),
        'adminOnly': Setting().get(PluginSettings.ADMIN_ONLY),
    }
    if details:
        result.update(utils.folderStatus(folder))
    return result


@access.user(scope=TokenScope.DATA_WRITE)
@boundHandler
@autoDescribeRoute(
    Description('Check out a folder, making local copies of its S3 files for a number of days.')
    .notes('If the folder is already checked out, its duration is changed.  A '
           'duration of 0 days releases the checkout.  Copying is done in a '
           'background task.')
    .modelParam('id', model=Folder, level=AccessType.WRITE)
    .param('days', 'The number of days to keep local copies.', dataType='integer')
    .param('progress', 'Whether to record progress on the copy.', dataType='boolean',
           default=True, required=False)
    .errorResponse('ID was invalid.')
    .errorResponse('Write access was denied for the folder.', 403)
)
def setFolderCheckout(self, folder, days, progress):
    user = self.getCurrentUser()
    _checkPermission(user)
    if days <= 0:
        return _release(user, folder, progress)
    maxDays = Setting().get(PluginSettings.MAX_DAYS)
    if days > maxDays:
        raise RestException('The checkout duration may not exceed %d days.' % maxDays)
    _requireAssetstore()
    _ensureWorker()
    checkout = Checkout().findByFolder(folder)
    if checkout is None:
        checkout = Checkout().createCheckout(folder, user, days)
    else:
        checkout = utils.updateCheckoutExpiry(checkout, days)
    tasks.checkoutFolderTask.delay(
        checkoutId=str(checkout['_id']), userId=str(user['_id']), progress=progress)
    return checkout


@access.user(scope=TokenScope.DATA_WRITE)
@boundHandler
@autoDescribeRoute(
    Description('Release the local checkout of a folder.')
    .notes('Local copies that no other checkout covers are removed in a background task.')
    .modelParam('id', model=Folder, level=AccessType.WRITE)
    .param('progress', 'Whether to record progress on the release.', dataType='boolean',
           default=True, required=False)
    .errorResponse('ID was invalid.')
    .errorResponse('Write access was denied for the folder.', 403)
)
def deleteFolderCheckout(self, folder, progress):
    user = self.getCurrentUser()
    _checkPermission(user)
    return _release(user, folder, progress)


def _release(user, folder, progress):
    checkout = Checkout().findByFolder(folder)
    if checkout is None:
        return {'released': False}
    _ensureWorker()
    Checkout().remove(checkout)
    tasks.detachCheckoutTask.delay(
        checkoutId=str(checkout['_id']), userId=str(user['_id']), progress=progress,
        folderName=folder['name'])
    return {'released': True}


class LocalCheckout(Resource):
    """Administrative endpoints for local checkouts."""

    def __init__(self):
        super().__init__()
        self.resourceName = 'local_checkout'
        self.route('GET', (), self.listCheckouts)
        self.route('POST', ('cleanup',), self.cleanup)

    @access.admin(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('List all local checkouts and summarize the space they use.')
        .pagingParams(defaultSort='expires', defaultSortDir=SortDir.ASCENDING)
    )
    def listCheckouts(self, limit, offset, sort):
        user = self.getCurrentUser()
        checkouts = list(Checkout().find({}, limit=limit, offset=offset, sort=sort))
        for checkout in checkouts:
            folder = Folder().load(checkout['folderId'], force=True)
            checkout['folderPath'] = (
                path_util.getResourcePath('folder', folder, user=user, force=True)
                if folder else None)
            owner = User().load(checkout['userId'], force=True) if checkout.get('userId') else None
            checkout['userLogin'] = owner['login'] if owner else None

        totals = next(CheckoutFile().collection.aggregate([
            {'$group': {'_id': None, 'count': {'$sum': 1}, 'bytes': {'$sum': '$size'}}}
        ]), {'count': 0, 'bytes': 0})
        assetstore = utils.getTargetAssetstore()
        capacity = None
        if assetstore is not None:
            capacity = assetstore_utilities.getAssetstoreAdapter(assetstore).capacityInfo()
        return {
            'checkouts': checkouts,
            'localFileCount': totals['count'],
            'localBytes': totals['bytes'],
            'assetstore': {
                'id': assetstore['_id'],
                'name': assetstore['name'],
                'capacity': capacity,
            } if assetstore else None,
        }

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Remove expired checkouts and release their local copies now.')
        .notes('This is otherwise done daily and before each checkout.')
    )
    def cleanup(self):
        return {'released': utils.cleanupExpired()}
