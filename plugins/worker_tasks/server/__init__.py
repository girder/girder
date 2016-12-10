from girder import events
from girder.constants import registerAccessFlag, AccessType, TokenScope
from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter
from .constants import ACCESS_FLAG_EXECUTE_TASK, TOKEN_SCOPE_EXECUTE_TASK
from .rest import WorkerTask


def _onJobSave(event):
    """
    If a job is finalized (i.e. success or failure status) and contains
    a temp token, we remove the token.
    """
    job = event.info

    if 'workerTaskTempToken' in job and job['status'] in (JobStatus.ERROR, JobStatus.SUCCESS):
        token = ModelImporter.model('token').load(
            job['workerTaskTempToken'], objectId=False, force=True)
        if token:
            ModelImporter.model('token').remove(token)

        # Remove the workerTaskTempToken field from the job
        ModelImporter.model('job', 'jobs').update({'_id': job['_id']}, update={
            '$unset': {'workerTaskTempToken': True}
        }, multi=False)


def load(info):
    registerAccessFlag(ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    TokenScope.describeScope(
        TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute tasks in the worker.')

    ModelImporter.model('item').ensureIndex('meta.workerTaskSpec')
    ModelImporter.model('job', 'jobs').exposeFields(level=AccessType.READ, fields={
        'workerTaskItemId', 'workerTaskBindings'})

    events.bind('model.job.save.after', info['name'], _onJobSave)

    info['apiRoot'].worker_task = WorkerTask()
