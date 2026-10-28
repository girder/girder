from pathlib import Path

from girder import events, plugin
from girder.utility.filesystem_assetstore_adapter import FilesystemAssetstoreAdapter
from girder.utility.model_importer import ModelImporter

from . import rest, utils
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


def _onFolderRemove(event):
    checkout = Checkout().findByFolder(event.info)
    if checkout is not None:
        utils.removeCheckout(checkout)


def _maybeCleanup(event):
    """
    Schedule the daily cleanup of expired local copies if it is due.  This is
    bound to a frequent event so that it runs even on idle servers.
    """
    # Imported here to avoid a circular import through girder_worker's plugin
    # discovery when girder.tasks is first loaded
    from girder.tasks import is_local_worker_available

    if is_local_worker_available() and utils.cleanupIsDue():
        from . import tasks

        tasks.cleanupTask.delay()


class LocalCheckoutPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'Local Checkout'

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
        events.bind('model.file.download.request', 'local_checkout', _maybeCleanup)
        _wrapUploadMethods()

        plugin.registerPluginStaticContent(
            plugin='local_checkout',
            css=['/style.css'],
            js=['/girder-plugin-local-checkout.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
