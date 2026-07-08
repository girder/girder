import logging

from girder_worker.app import app

from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.user import User
from girder.utility._cache import hourCache as _hourCache
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext

logger = logging.getLogger(__name__)


@_hourCache.cache_on_arguments()
def is_local_worker_available():
    """
    Check if a local worker is available to process tasks.

    This function checks if at least one worker is actively consuming from the
    'local' queue by inspecting Celery's control interface.
    When celery is configured with task_always_eager=True, tasks execute
    in-process and no external worker is needed. In this case, we return True.

    :returns: True if a worker is available or if running in eager mode.
    """
    # If celery is configured for eager execution no worker is needed
    if app.conf.task_always_eager:
        return True
    try:
        # Get an inspector object to check worker status
        status = app.control.inspect()
        # When workers are connected and consuming from queues, stats will
        # return a dict; otherwise stats will be None
        stats = status.stats()
        if stats is None or (isinstance(stats, dict) and len(stats) == 0):
            return False
        # Also check active_queues to ensure we have workers on the local queue
        active_queues = status.active_queues()
        if active_queues is None:
            return False
        # Check if any worker has the 'local' queue
        for _, queues in active_queues.items():
            if isinstance(queues, list):
                for queue_info in queues:
                    if isinstance(queue_info, dict) and queue_info.get('name') == 'local':
                        return True
        return False
    except Exception as e:
        logger.warning('Failed to check local worker availability: %s', str(e))
        return False


def ensure_local_worker_available():
    """
    Check if a local worker is available, raising an exception if not.

    Call this before sending tasks to the 'local' queue.  It raises a
    RestException with HTTP 503 status if no worker is available.
    """
    from girder.exceptions import RestException

    if not is_local_worker_available():
        raise RestException('No local worker is available to process this request.', code=503)


@app.task(queue='local')
def importDataTask(
    assetstoreId: str,
    parentId: str,
    parentType: str,
    params: dict,
    progress: bool,
    userId: str,
    leafFoldersAsItems: bool
):
    user = User().load(userId, force=True)
    assetstore = Assetstore().load(assetstoreId)
    parent = ModelImporter.model(parentType).load(parentId, force=True)

    with ProgressContext(progress, user=user, title='Importing data') as ctx:
        Assetstore().importData(
            assetstore, parent=parent, parentType=parentType, params=params,
            progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems,
        )


@app.task(queue='local')
def deleteFolderTask(
    folderId: str,
    progress: bool,
    userId: str,
    contentsOnly: bool = False,
):
    user = User().load(userId, force=True)
    folder = Folder().load(folderId, force=True)

    with ProgressContext(progress, user=user,
                         title=f'Deleting folder {folder["name"]}',
                         message='Calculating folder size...') as ctx:
        if progress:
            total = Folder().subtreeCount(folder)
            if contentsOnly:
                total -= 1
            ctx.update(total=total)

        if contentsOnly:
            Folder().clean(folder, progress=ctx)
        else:
            Folder().remove(folder, progress=ctx)


@app.task(queue='local')
def deleteCollectionTask(
    collectionId: str,
    progress: bool,
    userId: str,
):
    user = User().load(userId, force=True)
    collection = Collection().load(collectionId, force=True)

    with ProgressContext(progress, user=user,
                         title=f'Deleting collection {collection["name"]}',
                         message='Calculating collection size...') as ctx:
        if progress:
            total = Collection().subtreeCount(collection)
            ctx.update(total=total)

        Collection().remove(collection, progress=ctx)


@app.task(queue='local')
def copyFolderTask(
    folderId: str,
    parentType: str,
    parentId: str | None,
    name: str,
    description: str,
    public: bool,
    progress: bool,
    userId: str,
):
    user = User().load(userId, force=True)
    folder = Folder().load(folderId, force=True)

    if parentId:
        parent = ModelImporter.model(parentType).load(parentId, force=True)
    else:
        parent = None

    with ProgressContext(progress, user=user,
                         title=f'Copying folder {folder["name"]}',
                         message='Calculating folder size...') as ctx:
        if progress:
            ctx.update(total=Folder().subtreeCount(folder))
        Folder().copyFolder(
            folder, creator=user, name=name, parentType=parentType,
            parent=parent, description=description, public=public, progress=ctx)
