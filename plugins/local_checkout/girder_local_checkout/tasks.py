from girder_worker.app import app

from girder.models.folder import Folder
from girder.models.user import User
from girder.utility.progress import ProgressContext

from . import utils
from .models import Checkout


@app.task(queue='local')
def checkoutFolderTask(checkoutId: str, userId: str, progress: bool):
    user = User().load(userId, force=True)
    checkout = Checkout().load(checkoutId)
    if checkout is None:
        return
    folder = Folder().load(checkout['folderId'], force=True)
    title = 'Making folder "%s" local' % (folder['name'] if folder else checkout['folderId'])
    with ProgressContext(progress, user=user, title=title) as ctx:
        utils.runCheckout(checkout, ctx)


@app.task(queue='local')
def detachCheckoutTask(checkoutId: str, userId: str, progress: bool, folderName: str):
    user = User().load(userId, force=True)
    with ProgressContext(progress, user=user,
                         title='Releasing local copies of folder "%s"' % folderName) as ctx:
        utils.detachCheckout(checkoutId)
        ctx.update(message='Done', force=True)


@app.task(queue='local')
def cleanupTask():
    return utils.cleanupExpired()
