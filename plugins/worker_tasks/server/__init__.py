from girder.constants import registerAccessFlag
from girder.utility.model_importer import ModelImporter
from .constants import ACCESS_FLAG_EXECUTE_TASK
from .rest import WorkerTask


def load(info):
    registerAccessFlag(ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    ModelImporter.model('item').ensureIndex('meta.workerTaskSpec')

    info['apiRoot'].worker_task = WorkerTask()
