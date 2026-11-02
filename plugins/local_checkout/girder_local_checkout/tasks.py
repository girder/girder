import logging
import threading
import traceback

from girder import events
from girder.models.folder import Folder
from girder.models.user import User
from girder.utility.progress import ProgressContext
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from . import utils
from .models import Checkout

logger = logging.getLogger(__name__)


def _runInThread(target, name):
    """
    Run a callable in a new daemon thread.  Tests replace this to run the
    work synchronously.
    """
    threading.Thread(target=target, name=name, daemon=True).start()


def _scheduleJob(title, jobType, function, user, kwargs):
    """
    Create a local job that runs a function of this module and schedule it in
    a thread of its own.  The Girder events daemon is not used because it
    handles one event at a time, and copying a large folder would hold up
    everything else that runs on it.
    """
    job = Job().createLocalJob(
        title=title, type=jobType, user=user, public=False,
        module=__name__, function=function, kwargs=kwargs)
    _runInThread(lambda: Job().scheduleJob(job), 'local_checkout-%s' % job['_id'])
    return job


def _runJob(job, work):
    """
    Run the work of a local job, recording its outcome on the job document.
    Failures are logged rather than raised, since the job runs in a thread
    where nothing could handle them.
    """
    Job().updateJob(job, status=JobStatus.RUNNING)
    try:
        result = work(**job['kwargs'])
    except Exception:
        logger.exception('Local checkout job %s failed', job['_id'])
        Job().updateJob(job, status=JobStatus.ERROR, log=traceback.format_exc())
        return None
    Job().updateJob(job, status=JobStatus.SUCCESS,
                    log='' if result is None else str(result))
    return result


def scheduleCheckout(checkout, folder, user, progress):
    """
    Schedule the copying of a checkout's files.
    """
    return _scheduleJob(
        'Making folder "%s" local' % folder['name'], 'local_checkout.checkout',
        'checkoutFolderTask', user, {
            'checkoutId': str(checkout['_id']),
            'userId': str(user['_id']),
            'progress': progress,
        })


def scheduleDetach(checkout, folder, user, progress):
    """
    Schedule the release of the local copies a checkout no longer covers.
    """
    return _scheduleJob(
        'Releasing local copies of folder "%s"' % folder['name'],
        'local_checkout.release', 'detachCheckoutTask', user, {
            'checkoutId': str(checkout['_id']),
            'userId': str(user['_id']),
            'progress': progress,
            'folderName': folder['name'],
        })


def scheduleCleanup():
    """
    Run the cleanup of expired local copies on the events daemon.
    """
    events.daemon.trigger(callback=cleanupTask)


def _checkoutFolder(checkoutId, userId, progress):
    user = User().load(userId, force=True)
    checkout = Checkout().load(checkoutId)
    if checkout is None:
        return 'The checkout was released before it started.'
    folder = Folder().load(checkout['folderId'], force=True)
    title = 'Making folder "%s" local' % (folder['name'] if folder else checkout['folderId'])
    with ProgressContext(progress, user=user, title=title) as ctx:
        utils.runCheckout(checkout, ctx)
    checkout = Checkout().load(checkoutId)
    if checkout is None:
        return 'The checkout was released while it was running.'
    summary = '%d of %d files are local; status: %s.' % (
        checkout['localCount'], checkout['fileCount'], checkout['status'])
    if checkout.get('message'):
        summary += '  ' + checkout['message']
    return summary


def _detachCheckout(checkoutId, userId, progress, folderName):
    user = User().load(userId, force=True)
    with ProgressContext(progress, user=user,
                         title='Releasing local copies of folder "%s"' % folderName) as ctx:
        released = utils.detachCheckout(checkoutId)
        ctx.update(message='Done', force=True)
    return 'Released %d local %s.' % (released, 'copy' if released == 1 else 'copies')


def checkoutFolderTask(job):
    return _runJob(job, _checkoutFolder)


def detachCheckoutTask(job):
    return _runJob(job, _detachCheckout)


def cleanupTask(event=None):
    try:
        return utils.cleanupExpired()
    except Exception:
        logger.exception('Failed to clean up expired local checkouts')
