from girder import events, plugin
from girder.exceptions import ValidationException
from girder.utility.filesystem_assetstore_adapter import FilesystemAssetstoreAdapter
from girder.utility.model_importer import ModelImporter

from . import rest, tasks, utils
from .models import Checkout, CheckoutFile


def _wrapUploadMethods():
    """
    Make the filesystem assetstore adapter release local copies rather than
    reject an upload when it is short of space.
    """
    if getattr(FilesystemAssetstoreAdapter, '_localCheckoutWrapped', False):
        return
    for name in ('initUpload', 'uploadChunk'):
        base = getattr(FilesystemAssetstoreAdapter, name)

        def wrapper(self, upload, *args, _base=base, **kwargs):
            utils.makeRoomForUpload(self, upload)
            return _base(self, upload, *args, **kwargs)

        wrapper.__name__ = name
        wrapper.__doc__ = base.__doc__
        setattr(FilesystemAssetstoreAdapter, name, wrapper)
    FilesystemAssetstoreAdapter._localCheckoutWrapped = True


def _onFileRemove(event):
    """
    When a checked-out file is deleted, core removes the local copy; we must
    also remove the original data it came from.
    """
    record = CheckoutFile().findByFile(event.info)
    if record is None:
        return
    utils.deleteOriginal(record)
    CheckoutFile().remove(record)


def _onFileReplaced(event):
    """
    When the contents of a checked-out file are replaced (including being
    moved to another assetstore), core has already discarded the local copy,
    so the original data is no longer needed either.
    """
    if 'fileId' not in event.info['upload']:
        return
    record = CheckoutFile().findByFile(event.info['file'])
    if record is None:
        return
    utils.deleteOriginal(record)
    CheckoutFile().remove(record)


def _onAssetstoreRemove(event):
    """
    Refuse to delete an assetstore that still holds the original data of a
    checked-out file; core only sees that those files point elsewhere.
    """
    if CheckoutFile().findOne(
            {'originalAssetstoreId': event.info['_id']}, fields=['_id']) is not None:
        raise ValidationException(
            'You may not delete an assetstore that contains the original data of '
            'files with local copies; release the checkouts first.')


def _onFolderRemove(event):
    checkout = Checkout().findByFolder(event.info)
    if checkout is not None:
        utils.removeCheckout(checkout)


def _maybeCleanup(event):
    """
    Schedule the daily cleanup of expired local copies if it is due.  This is
    bound to a frequent event so that it runs even on idle servers.
    """
    if utils.cleanupIsDue():
        tasks.scheduleCleanup()


class LocalCheckoutPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'Local Checkout'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        plugin.getPlugin('jobs').load(info)

        ModelImporter.registerModel('localCheckout', Checkout, 'local_checkout')
        ModelImporter.registerModel('localCheckoutFile', CheckoutFile, 'local_checkout')

        info['apiRoot'].local_checkout = rest.LocalCheckout()
        info['apiRoot'].folder.route('GET', (':id', 'local_checkout'), rest.getFolderCheckout)
        info['apiRoot'].folder.route('PUT', (':id', 'local_checkout'), rest.setFolderCheckout)
        info['apiRoot'].folder.route('DELETE', (':id', 'local_checkout'),
                                     rest.deleteFolderCheckout)

        events.bind('model.file.remove', 'local_checkout', _onFileRemove)
        events.bind('model.file.finalizeUpload.before', 'local_checkout', _onFileReplaced)
        events.bind('model.folder.remove', 'local_checkout', _onFolderRemove)
        events.bind('model.assetstore.remove', 'local_checkout', _onAssetstoreRemove)
        events.bind('model.file.download.request', 'local_checkout', _maybeCleanup)
        _wrapUploadMethods()
