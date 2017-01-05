from girder import events
from girder.constants import registerAccessFlag, AccessType, TokenScope
from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter
from .constants import ACCESS_FLAG_EXECUTE_TASK, TOKEN_SCOPE_EXECUTE_TASK
from .rest import ItemTask


def _onJobSave(event):
    """
    If a job is finalized (i.e. success or failure status) and contains
    a temp token, we remove the token.
    """
    job = event.info

    if 'itemTaskTempToken' in job and job['status'] in (JobStatus.ERROR, JobStatus.SUCCESS):
        token = ModelImporter.model('token').load(
            job['itemTaskTempToken'], objectId=False, force=True)
        if token:
            ModelImporter.model('token').remove(token)

        # Remove the itemTaskTempToken field from the job
        ModelImporter.model('job', 'jobs').update({'_id': job['_id']}, update={
            '$unset': {'itemTaskTempToken': True}
        }, multi=False)


def load(info):
    registerAccessFlag(ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    TokenScope.describeScope(
        TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute item tasks.')

    ModelImporter.model('item').ensureIndex('meta.itemTaskSpec')
    ModelImporter.model('job', 'jobs').exposeFields(level=AccessType.READ, fields={
        'itemTaskId', 'itemTaskBindings'})

    events.bind('model.job.save.after', info['name'], _onJobSave)

    info['apiRoot'].item_task = ItemTask()
