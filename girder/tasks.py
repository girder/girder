from girder.models.assetstore import Assetstore
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.user import User
from girder.utility.progress import ProgressContext
from girder_worker.app import app


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
    parent = Folder().load(parentId, force=True)
    with ProgressContext(progress, user=user, title='Importing data') as ctx:
        Assetstore().importData(
            assetstore, parent=parent, parentType=parentType, params=params,
            progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems,
        )


@app.task(queue='local')
def deleteFolderTask(
    folder: dict,
    progress: bool,
    user: dict,
    contentsOnly: bool = False,
):
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
    collection: dict,
    progress: bool,
    user: dict,
):
    with ProgressContext(progress, user=user,
                         title=f'Deleting collection {collection["name"]}',
                         message='Calculating collection size...') as ctx:
        if progress:
            total = Collection().subtreeCount(collection)
            ctx.update(total=total)

        Collection().remove(collection, progress=ctx)


@app.task(queue='local')
def copyFolderTask(
    folder: dict,
    parentType: str,
    parent: dict,
    name: str,
    description: str,
    public: bool,
    progress: bool,
    user: dict,
):
    with ProgressContext(progress, user=user,
                         title=f'Copying folder {folder["name"]}',
                         message='Calculating folder size...') as ctx:
        if progress:
            ctx.update(total=Folder().subtreeCount(folder))
        Folder().copyFolder(
            folder, creator=user, name=name, parentType=parentType,
            parent=parent, description=description, public=public, progress=ctx)
