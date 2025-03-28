from girder.models.assetstore import Assetstore
from girder.utility.progress import ProgressContext
from girder_worker.app import app


@app.task(queue='local')
def importDataTask(
    assetstore: dict,
    parent: dict,
    parentType: str,
    params: dict,
    progress: bool,
    user: dict,
    leafFoldersAsItems: bool
):
    with ProgressContext(progress, user=user, title='Importing data') as ctx:
        Assetstore().importData(
            assetstore, parent=parent, parentType=parentType, params=params,
            progress=ctx, user=user, leafFoldersAsItems=leafFoldersAsItems,
        )
