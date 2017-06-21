import json

from girder import events
from girder.constants import registerAccessFlag, AccessType, TokenScope
from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter
from . import constants
from .rest import ItemTask
from .json_tasks import createItemTasksFromJson, configureItemTaskFromJson, \
    runJsonTasksDescriptionForFolder, runJsonTasksDescriptionForItem
from .slicer_cli_tasks import configureItemTaskFromSlicerCliXml, createItemTasksFromSlicerCliXml, \
    runSlicerCliTasksDescriptionForFolder, runSlicerCliTasksDescriptionForItem


def _onJobSave(event):
    """
    If a job is finalized (i.e. success or failure status) and contains
    a temp token, we remove the token.
    """
    params = event.info['params']
    job = event.info['job']

    if 'itemTaskTempToken' in job and params['status'] in (JobStatus.ERROR, JobStatus.SUCCESS):
        token = ModelImporter.model('token').load(
            job['itemTaskTempToken'], objectId=False, force=True)
        if token:
            ModelImporter.model('token').remove(token)

        # Remove the itemTaskTempToken field from the job
        ModelImporter.model('job', 'jobs').update({'_id': job['_id']}, update={
            '$unset': {'itemTaskTempToken': True}
        }, multi=False)
        del job['itemTaskTempToken']


def _onUpload(event):
    """
    Look at uploads containing references related to this plugin. If found,
    they are used to link item task outputs back to a job document.
    """
    try:
        ref = json.loads(event.info.get('reference'))
    except (ValueError, TypeError):
        return

    if isinstance(ref, dict) and ref.get('type') == 'item_tasks.output':
        jobModel = ModelImporter.model('job', 'jobs')
        tokenModel = ModelImporter.model('token')
        token = event.info['currentToken']

        if tokenModel.hasScope(token, 'item_tasks.job_write:%s' % ref['jobId']):
            job = jobModel.load(ref['jobId'], force=True, exc=True)
        else:
            job = jobModel.load(
                ref['jobId'], level=AccessType.WRITE, user=event.info['currentUser'], exc=True)

        file = event.info['file']
        item = ModelImporter.model('item').load(file['itemId'], force=True)

        # Add link to job model to the output item
        jobModel.updateJob(job, otherFields={
            'itemTaskBindings.outputs.%s.itemId' % ref['id']: item['_id']
        })

        # Also a link in the item to the job that created it
        item['createdByJob'] = job['_id']
        ModelImporter.model('item').save(item)


def load(info):
    registerAccessFlag(constants.ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute item tasks.')
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_AUTO_CREATE_CLI, 'Item task auto-creation',
        'Create new CLIs via automatic introspection.', admin=True)

    ModelImporter.model('item').ensureIndex(['meta.isItemTask', {'sparse': True}])
    ModelImporter.model('item').exposeFields(level=AccessType.READ, fields='createdByJob')
    ModelImporter.model('job', 'jobs').exposeFields(level=AccessType.READ, fields={
        'itemTaskId', 'itemTaskBindings'})

    events.bind('jobs.job.update', info['name'], _onJobSave)
    events.bind('data.process', info['name'], _onUpload)

    info['apiRoot'].item_task = ItemTask()

    info['apiRoot'].item.route('POST', (':id', 'item_task_slicer_cli_description'),
                               runSlicerCliTasksDescriptionForItem)
    info['apiRoot'].item.route('PUT', (':id', 'item_task_slicer_cli_xml'),
                               configureItemTaskFromSlicerCliXml)
    info['apiRoot'].item.route('POST', (':id', 'item_task_json_description'),
                               runJsonTasksDescriptionForItem)
    info['apiRoot'].item.route('PUT', (':id', 'item_task_json_specs'),
                               configureItemTaskFromJson)

    info['apiRoot'].folder.route('POST', (':id', 'item_task_slicer_cli_description'),
                                 runSlicerCliTasksDescriptionForFolder)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_slicer_cli_xml'),
                                 createItemTasksFromSlicerCliXml)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_json_description'),
                                 runJsonTasksDescriptionForFolder)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_json_specs'),
                                 createItemTasksFromJson)
