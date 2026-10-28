from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource, boundHandler
from girder.constants import AccessType, SortDir, TokenScope
from girder.exceptions import GirderException, RestException
from girder.models.assetstore import Assetstore
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
        raise RestException('Only administrators may checkout folders.', code=403)


def _ensureWorker():
    # Imported here to avoid a circular import through girder_worker's plugin
    # discovery when girder.tasks is first loaded
    from girder.tasks import ensure_local_worker_available

    ensure_local_worker_available()


def _requireAssetstore(assetstoreId):
    try:
        return utils.resolveCheckoutAssetstore(assetstoreId)
    except GirderException as exc:
        raise RestException(str(exc))


def _assetstoreInfo(assetstore):
    capacity = assetstore_utilities.getAssetstoreAdapter(assetstore).capacityInfo()
    return {'_id': assetstore['_id'], 'name': assetstore['name'], 'free': capacity.get('free')}


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
    # When there is no configured or default filesystem assetstore, the user
    # chooses one of these
    choices = [] if assetstore else [
        _assetstoreInfo(choice) for choice in utils.getFilesystemAssetstores()]
    result = {
        'checkout': Checkout().findByFolder(folder),
        'enabled': assetstore is not None or bool(choices),
        'assetstoreName': assetstore['name'] if assetstore else None,
        'assetstores': choices,
        'maxDays': Setting().get(PluginSettings.MAX_DAYS),
        'adminOnly': Setting().get(PluginSettings.ADMIN_ONLY),
    }
    if details:
        result.update(utils.folderStatus(folder))
    return result


@access.user(scope=TokenScope.DATA_WRITE)
@boundHandler
@autoDescribeRoute(
    Description('Checkout a folder, making local copies of its S3 files for a number of days.')
    .notes('If the folder is already checked out, its duration is changed.  A '
           'duration of 0 days releases the checkout.  Copying is done in a '
           'background task.')
    .modelParam('id', model=Folder, level=AccessType.WRITE)
    .param('days', 'The number of days to keep local copies.', dataType='integer')
    .param('assetstoreId', 'The filesystem assetstore to copy files to.  This is only '
           'used when no assetstore is configured for local checkouts and the default '
           'assetstore is not a filesystem assetstore; it may be omitted if there is only '
           'one filesystem assetstore.', required=False)
    .param('progress', 'Whether to record progress on the copy.', dataType='boolean',
           default=True, required=False)
    .errorResponse('ID was invalid.')
    .errorResponse('Write access was denied for the folder.', 403)
)
def setFolderCheckout(self, folder, days, assetstoreId, progress):
    user = self.getCurrentUser()
    _checkPermission(user)
    if days <= 0:
        return _release(user, folder, progress)
    maxDays = Setting().get(PluginSettings.MAX_DAYS)
    if days > maxDays:
        raise RestException('The checkout duration may not exceed %d days.' % maxDays)
    checkout = Checkout().findByFolder(folder)
    if not assetstoreId and checkout is not None:
        assetstoreId = checkout.get('assetstoreId')
    assetstore = _requireAssetstore(assetstoreId)
    _ensureWorker()
    if checkout is None:
        checkout = Checkout().createCheckout(folder, user, days, assetstore)
    else:
        checkout = utils.updateCheckoutExpiry(checkout, days, assetstore)
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
        self.route('GET', ('settings',), self.getSettings)
        self.route('POST', ('cleanup',), self.cleanup)

    @access.public
    @autoDescribeRoute(
        Description('Get the settings that affect whether a user may checkout folders.')
    )
    def getSettings(self):
        return {
            'adminOnly': Setting().get(PluginSettings.ADMIN_ONLY),
            'maxDays': Setting().get(PluginSettings.MAX_DAYS),
        }

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
            assetstore = (Assetstore().load(checkout['assetstoreId'])
                          if checkout.get('assetstoreId') else None)
            checkout['assetstoreName'] = assetstore['name'] if assetstore else None

        perAssetstore = {
            entry['_id']: entry for entry in CheckoutFile().collection.aggregate([
                {'$group': {'_id': '$localAssetstoreId', 'count': {'$sum': 1},
                            'bytes': {'$sum': '$size'}}}
            ])}
        # Summarize the assetstores that hold local copies or can receive them
        target = utils.getTargetAssetstore()
        candidates = [target] if target else utils.getFilesystemAssetstores()
        candidateIds = {assetstore['_id'] for assetstore in candidates}
        candidates += [assetstore for assetstore in (
            Assetstore().load(assetstoreId) for assetstoreId in perAssetstore
            if assetstoreId not in candidateIds) if assetstore is not None]
        assetstores = []
        for assetstore in candidates:
            totals = perAssetstore.get(assetstore['_id'], {'count': 0, 'bytes': 0})
            assetstores.append({
                'id': assetstore['_id'],
                'name': assetstore['name'],
                'capacity': assetstore_utilities.getAssetstoreAdapter(
                    assetstore).capacityInfo(),
                'localFileCount': totals['count'],
                'localBytes': totals['bytes'],
            })
        return {
            'checkouts': checkouts,
            'localFileCount': sum(entry['count'] for entry in perAssetstore.values()),
            'localBytes': sum(entry['bytes'] for entry in perAssetstore.values()),
            'assetstores': assetstores,
        }

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Remove expired checkouts and release their local copies now.')
        .notes('This is otherwise done daily and before each checkout.')
    )
    def cleanup(self):
        return {'released': utils.cleanupExpired()}
