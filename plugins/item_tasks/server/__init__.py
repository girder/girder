from girder import events
from girder.api.rest import getCurrentToken, getCurrentUser
from girder.constants import registerAccessFlag, AccessType, TokenScope
from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter
from . import constants
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


def _onUpload(event):
    """
    Look at uploads containing references related to this plugin. If found,
    they are used to link item task outputs back to a job document.
    """
    ref = event.info.get('reference', '')
    if ref.startswith('item_tasks.output'):
        key, jobId = ref.split(':')[-2:]
        jobModel = ModelImporter.model('job', 'jobs')
        tokenModel = ModelImporter.model('token')

        if tokenModel.hasScope(getCurrentToken(), 'item_tasks.job_write:%s' % jobId):
            job = jobModel.load(jobId, force=True, exc=True)
        else:
            job = jobModel.load(jobId, level=AccessType.WRITE, user=getCurrentUser(), exc=True)

        file = event.info['file']
        item = ModelImporter.model('item').load(file['itemId'], force=True)

        job['itemTaskBindings']['outputs'][key]['itemId'] = item['_id']
        jobModel.save(job)


def load(info):
    registerAccessFlag(constants.ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute item tasks.')
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_AUTO_CREATE_CLI, 'Item task auto-creation',
        'Create new CLIs via automatic introspection.', admin=True)

    ModelImporter.model('item').ensureIndex('meta.itemTaskSpec')
    ModelImporter.model('job', 'jobs').exposeFields(level=AccessType.READ, fields={
        'itemTaskId', 'itemTaskBindings'})

    events.bind('model.job.save.after', info['name'], _onJobSave)
    events.bind('data.process', info['name'], _onUpload)

    info['apiRoot'].item_task = ItemTask()
