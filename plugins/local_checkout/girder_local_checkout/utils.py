import datetime
import io
import logging
import time

from bson.objectid import ObjectId

from girder.constants import AssetstoreType
from girder.exceptions import GirderException
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.utility import assetstore_utilities
from girder.utility.progress import noProgress

from .models import Checkout, CheckoutFile, CheckoutStatus
from .settings import PluginSettings

logger = logging.getLogger(__name__)

# File document keys that describe where a file's data lives.  These are
# snapshotted when a file is made local and restored when it is released.
LOCATION_KEYS = ('assetstoreId', 's3Key', 'relpath', 'imported', 'path', 'sha512', 'mtime')

# How often a server process checks whether the daily cleanup is due.
CLEANUP_CHECK_INTERVAL = 600
CLEANUP_INTERVAL = datetime.timedelta(days=1)

_lastCleanupCheck = 0


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def getTargetAssetstore():
    """
    Return the filesystem assetstore that local copies are placed in, or None
    if no suitable assetstore is configured.
    """
    assetstoreId = Setting().get(PluginSettings.ASSETSTORE_ID)
    if assetstoreId:
        assetstore = Assetstore().load(ObjectId(assetstoreId))
    else:
        try:
            assetstore = Assetstore().getCurrent()
        except GirderException:
            return None
    if assetstore is None or assetstore['type'] != AssetstoreType.FILESYSTEM:
        return None
    return assetstore


def getAssetstoreTypes():
    return {assetstore['_id']: assetstore['type'] for assetstore in Assetstore().find()}


def isSourceFile(file, assetstoreTypes):
    """
    Return True if a file's data lives on an assetstore that can be checked
    out (currently only S3 assetstores).
    """
    return assetstoreTypes.get(file.get('assetstoreId')) == AssetstoreType.S3


def walkFiles(folder):
    """
    Yield every file document in a folder's items, recursively.
    """
    # Eagerly evaluate the lists, as cursors can time out on long operations
    for item in list(Folder().childItems(folder, fields=['_id'])):
        yield from list(File().find({'itemId': item['_id']}))
    subfolders = Folder().find(
        {'parentId': folder['_id'], 'parentCollection': 'folder'}, fields=['_id'])
    for sub in list(subfolders):
        yield from walkFiles(sub)


def folderStatus(folder):
    """
    Summarize how much of a folder's checkout-able data is currently local.
    """
    assetstoreTypes = getAssetstoreTypes()
    status = {'fileCount': 0, 'localCount': 0, 'bytes': 0, 'localBytes': 0}
    for file in walkFiles(folder):
        size = file.get('size') or 0
        record = CheckoutFile().findByFile(file)
        if record is not None:
            status['fileCount'] += 1
            status['localCount'] += 1
            status['bytes'] += size
            status['localBytes'] += size
        elif isSourceFile(file, assetstoreTypes):
            status['fileCount'] += 1
            status['bytes'] += size
    return status


def freeSpace(adapter):
    """
    Return the free space on an assetstore (already accounting for the
    reserved space), or None if it is unknown.
    """
    return adapter.capacityInfo().get('free')


def makeLocal(file, assetstore, adapter, checkout):
    """
    Copy a file's data into the filesystem assetstore and point the file
    document at the copy, recording where the data originally lived.
    """
    upload = adapter.initUpload({'size': file['size'], 'received': 0}, None)
    try:
        if file['size'] > 0:
            stream = File().getAssetstoreAdapter(file).downloadFile(file, headers=False)
            # Adapters reject chunks below the minimum chunk size, so gather
            # the streamed data into larger chunks
            chunkSize = Upload()._getChunkSize()
            buffered = []
            bufferedLen = 0
            for data in stream():
                buffered.append(data)
                bufferedLen += len(data)
                if bufferedLen >= chunkSize:
                    upload = adapter.uploadChunk(upload, io.BytesIO(b''.join(buffered)), None)
                    buffered = []
                    bufferedLen = 0
            if buffered:
                upload = adapter.uploadChunk(upload, io.BytesIO(b''.join(buffered)), None)
        if upload['received'] != file['size']:
            raise GirderException('Received %d of %d bytes for file %s' % (
                upload['received'], file['size'], file['_id']))
        localDoc = adapter.finalizeUpload(upload, dict(file))
    except Exception:
        adapter.cancelUpload(upload)
        raise

    record = CheckoutFile().save({
        'fileId': file['_id'],
        'name': file['name'],
        'size': file['size'],
        'originalAssetstoreId': file['assetstoreId'],
        'original': {key: file[key] for key in LOCATION_KEYS if key in file},
        'localAssetstoreId': assetstore['_id'],
        'path': localDoc['path'],
        'sha512': localDoc['sha512'],
        'checkoutIds': [checkout['_id']],
        'expires': checkout['expires'],
        'created': _now(),
    })
    _setLocation(file, {
        'assetstoreId': assetstore['_id'],
        'path': localDoc['path'],
        'sha512': localDoc['sha512'],
    })
    return record


def _setLocation(file, location):
    """
    Replace the location keys of a file document, both in the database and in
    the in-memory document.
    """
    update = {'$set': location}
    unset = {key: '' for key in LOCATION_KEYS if key not in location}
    if unset:
        update['$unset'] = unset
    File().update({'_id': file['_id']}, update, multi=False)
    for key in LOCATION_KEYS:
        file.pop(key, None)
    file.update(location)


def releaseFile(record, file=None):
    """
    Remove a file's local copy and point the file back at its original data.

    :param record: the CheckoutFile record.
    :param file: the file document, if already loaded.  This is updated in
        place to refer to the original data.
    """
    if file is None:
        file = File().load(record['fileId'], force=True)
    if (file is not None and file.get('assetstoreId') == record['localAssetstoreId']
            and file.get('path') == record['path']):
        assetstore = Assetstore().load(record['localAssetstoreId'])
        if assetstore is not None:
            # This only unlinks the data if no other file refers to it
            assetstore_utilities.getAssetstoreAdapter(assetstore).deleteFile(file)
        _setLocation(file, record['original'])
    CheckoutFile().remove(record)
    if record.get('checkoutIds'):
        Checkout().update({'_id': {'$in': record['checkoutIds']}}, {
            '$inc': {'localCount': -1, 'bytes': -(record.get('size') or 0)}})


def deleteOriginal(record):
    """
    Delete the original S3 object of a checked-out file, if nothing else
    refers to it.  This is used when the file itself is deleted or its
    contents are replaced while a local copy exists.
    """
    original = record['original']
    if original.get('imported') or (record.get('size') or 0) <= 0 or 'relpath' not in original:
        return
    query = {'assetstoreId': original['assetstoreId'], 'relpath': original['relpath']}
    if File().findOne(query, fields=['_id']) is not None:
        return
    if CheckoutFile().findOne({
        '_id': {'$ne': record['_id']},
        'originalAssetstoreId': original['assetstoreId'],
        'original.relpath': original['relpath'],
    }, fields=['_id']) is not None:
        return
    assetstore = Assetstore().load(original['assetstoreId'])
    if assetstore is None or assetstore['type'] != AssetstoreType.S3:
        return
    adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
    try:
        adapter.client.delete_object(Bucket=assetstore['bucket'], Key=original['s3Key'])
    except Exception:
        logger.exception('Failed to delete original of file %s', record['fileId'])


def detachCheckout(checkoutId):
    """
    Remove a checkout's claim on its files, releasing any file that no other
    checkout covers.  The checkout document itself may already be gone.

    :returns: the number of files released.
    """
    checkoutId = ObjectId(checkoutId)
    released = 0
    for record in list(CheckoutFile().find({'checkoutIds': checkoutId})):
        record['checkoutIds'] = [i for i in record['checkoutIds'] if i != checkoutId]
        expires = CheckoutFile().computeExpires(record)
        if expires is None:
            releaseFile(record)
            released += 1
        else:
            CheckoutFile().update({'_id': record['_id']}, {
                '$set': {'checkoutIds': record['checkoutIds'], 'expires': expires}}, multi=False)
    return released


def removeCheckout(checkout):
    Checkout().remove(checkout)
    return detachCheckout(checkout['_id'])


def updateCheckoutExpiry(checkout, days):
    """
    Change the duration of a checkout, adjusting the expiration of every file
    it covers.
    """
    now = _now()
    checkout['days'] = days
    checkout['updated'] = now
    checkout['expires'] = now + datetime.timedelta(days=days)
    checkout['status'] = CheckoutStatus.PENDING
    checkout = Checkout().save(checkout)
    for record in list(CheckoutFile().find({'checkoutIds': checkout['_id']})):
        expires = CheckoutFile().computeExpires(record)
        if expires is not None and expires != record['expires']:
            CheckoutFile().update({'_id': record['_id']}, {'$set': {'expires': expires}},
                                  multi=False)
    return checkout


def cleanupExpired(now=None):
    """
    Remove expired checkouts and release every local copy whose expiration
    has passed.

    :returns: the number of files released.
    """
    now = now or _now()
    released = 0
    for checkout in list(Checkout().find({'expires': {'$lte': now}})):
        released += removeCheckout(checkout)
    for record in list(CheckoutFile().find({'expires': {'$lte': now}})):
        releaseFile(record)
        released += 1
    return released


def ensureSpace(adapter, size, expires=None):
    """
    Release the soonest-expiring local copies on an assetstore until at least
    ``size`` bytes are free.

    :param adapter: the adapter of the filesystem assetstore to make room on.
    :param size: the number of bytes needed.
    :param expires: if set, only release copies that expire before this time.
    :returns: True if there is enough space.
    """
    query = {'localAssetstoreId': adapter.assetstore['_id']}
    if expires is not None:
        query['expires'] = {'$lt': expires}
    while True:
        free = freeSpace(adapter)
        if free is None or free >= size:
            return True
        record = CheckoutFile().findOne(query, sort=[('expires', 1)])
        if record is None:
            return False
        logger.info('Evicting local copy of file %s to make room', record['fileId'])
        Checkout().update({'_id': {'$in': record.get('checkoutIds', [])}}, {'$set': {
            'status': CheckoutStatus.PARTIAL,
            'message': 'Some local copies were removed to make room for other data.',
        }})
        releaseFile(record)


def makeRoomForUpload(adapter, upload):
    """
    Before data is written to a filesystem assetstore, release local copies
    on it if the rest of the upload would not otherwise fit.  Uploads take
    precedence over checkouts of any duration.
    """
    needed = (upload.get('size') or 0) - (upload.get('received') or 0)
    if needed <= 0:
        return
    free = freeSpace(adapter)
    if free is None or free >= needed:
        return
    ensureSpace(adapter, needed)


def _gatherFiles(folder, checkout):
    """
    Extend the checkout to files that are already local and return the
    files that still need to be copied along with the local file count and
    size.
    """
    assetstoreTypes = getAssetstoreTypes()
    pending = []
    localCount = 0
    localBytes = 0
    for file in walkFiles(folder):
        record = CheckoutFile().findByFile(file)
        if record is not None:
            CheckoutFile().addCheckout(record, checkout)
            localCount += 1
            localBytes += file.get('size') or 0
        elif isSourceFile(file, assetstoreTypes):
            pending.append(file)
    return pending, localCount, localBytes


def runCheckout(checkout, progress=noProgress):
    """
    Make local copies of all checkout-able files in a checkout's folder.
    This is intended to be run from a background task.
    """
    checkoutId = checkout['_id']

    def _update(**fields):
        Checkout().update({'_id': checkoutId}, {'$set': fields}, multi=False)

    def _stillWanted():
        return Checkout().findOne({'_id': checkoutId}, fields=['_id']) is not None

    assetstore = getTargetAssetstore()
    if assetstore is None:
        _update(status=CheckoutStatus.ERROR,
                message='No filesystem assetstore is configured for local checkouts.')
        return
    adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
    folder = Folder().load(checkout['folderId'], force=True)
    if folder is None:
        removeCheckout(checkout)
        return
    _update(status=CheckoutStatus.RUNNING, message='')
    cleanupExpired()

    progress.update(message='Listing files')
    pending, localCount, localBytes = _gatherFiles(folder, checkout)
    fileCount = localCount + len(pending)
    _update(fileCount=fileCount, localCount=localCount, bytes=localBytes)
    progress.update(total=len(pending), current=0, force=True)

    status = CheckoutStatus.COMPLETE
    message = ''
    failures = 0
    for file in pending:
        if not _stillWanted():
            break
        if not ensureSpace(adapter, file.get('size') or 0, checkout['expires']):
            status = CheckoutStatus.PARTIAL
            message = 'Insufficient space on assetstore "%s"; %d of %d files were made local.' % (
                assetstore['name'], localCount, fileCount)
            break
        progress.update(message='Copying %s' % file['name'])
        try:
            makeLocal(file, assetstore, adapter, checkout)
            localCount += 1
            localBytes += file.get('size') or 0
        except Exception:
            logger.exception('Failed to make file %s local', file['_id'])
            failures += 1
        progress.update(increment=1)
        _update(localCount=localCount, bytes=localBytes)
    if failures and status == CheckoutStatus.COMPLETE:
        status = CheckoutStatus.PARTIAL
        message = '%d of %d files could not be copied.' % (failures, fileCount)
    _update(status=status, message=message, localCount=localCount, bytes=localBytes,
            updated=_now())
    progress.update(message=message or 'Done', force=True)
    if not _stillWanted():
        # The checkout was released while we were copying
        detachCheckout(checkoutId)


def _stateCollection():
    return Checkout().collection.database['localCheckoutState']


def cleanupIsDue():
    """
    Atomically claim the daily cleanup if it is due.  This is cheap to call
    often; it only consults the database every CLEANUP_CHECK_INTERVAL
    seconds per process, and only one server or worker wins the claim.
    """
    global _lastCleanupCheck

    if time.time() - _lastCleanupCheck < CLEANUP_CHECK_INTERVAL:
        return False
    _lastCleanupCheck = time.time()
    now = _now()
    _stateCollection().update_one(
        {'_id': 'cleanup'}, {'$setOnInsert': {'lastRun': now}}, upsert=True)
    claimed = _stateCollection().find_one_and_update(
        {'_id': 'cleanup', 'lastRun': {'$lte': now - CLEANUP_INTERVAL}},
        {'$set': {'lastRun': now}})
    return claimed is not None
