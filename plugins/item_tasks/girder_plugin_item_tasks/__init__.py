import json

from girder import events
from girder.constants import registerAccessFlag, AccessType, TokenScope
from girder.models.item import Item
from girder.models.token import Token
from girder.plugin import getPlugin, GirderPlugin
from girder_plugin_jobs.constants import JobStatus
from girder_plugin_jobs.models.job import Job

from . import constants
from .rest import ItemTask
from .json_tasks import createItemTasksFromJson, configureItemTaskFromJson, \
    runJsonTasksDescriptionForFolder, runJsonTasksDescriptionForItem
from .slicer_cli_tasks import configureItemTaskFromSlicerCliXml, createItemTasksFromSlicerCliXml, \
    runSlicerCliTasksDescriptionForFolder, runSlicerCliTasksDescriptionForItem
from .celery_tasks import describeCeleryTaskItem, celeryTaskDescriptionForFolder


def _onJobSave(event):
    """
    If a job is finalized (i.e. success or failure status) and contains
    a temp token, we remove the token.
    """
    params = event.info['params']
    job = event.info['job']

    if 'itemTaskTempToken' in job and params['status'] in (JobStatus.ERROR, JobStatus.SUCCESS):
        token = Token().load(job['itemTaskTempToken'], objectId=False, force=True)
        if token:
            Token().remove(token)

        # Remove the itemTaskTempToken field from the job
        Job().update({'_id': job['_id']}, update={
            '$unset': {'itemTaskTempToken': True}
        }, multi=False)
        del job['itemTaskTempToken']


def _onUpload(event):
    """
    Look at uploads containing references related to this plugin. If found,
    they are used to link item task outputs back to a job document.
    """
    try:
        ref = json.loads(event.info.get('reference', ''))
    except ValueError:
        return

    if isinstance(ref, dict) and ref.get('type') == 'item_tasks.output':
        jobModel = Job()
        tokenModel = Token()
        token = event.info['currentToken']

        if tokenModel.hasScope(token, 'item_tasks.job_write:%s' % ref['jobId']):
            job = jobModel.load(ref['jobId'], force=True, exc=True)
        else:
            job = jobModel.load(
                ref['jobId'], level=AccessType.WRITE, user=event.info['currentUser'], exc=True)

        file = event.info['file']
        item = Item().load(file['itemId'], force=True)

        # Add link to job model to the output item
        jobModel.updateJob(job, otherFields={
            'itemTaskBindings.outputs.%s.itemId' % ref['id']: item['_id']
        })

        # Also a link in the item to the job that created it
        item['createdByJob'] = job['_id']
        Item().save(item)


def load(info):
    registerAccessFlag(constants.ACCESS_FLAG_EXECUTE_TASK, name='Execute analyses', admin=True)
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_EXECUTE_TASK, name='Execute tasks', description='Execute item tasks.')
    TokenScope.describeScope(
        constants.TOKEN_SCOPE_AUTO_CREATE_CLI, 'Item task auto-creation',
        'Create new CLIs via automatic introspection.', admin=True)

    Item().ensureIndex(['meta.isItemTask', {'sparse': True}])
    Item().exposeFields(level=AccessType.READ, fields='createdByJob')
    Job().exposeFields(level=AccessType.READ, fields={'itemTaskId', 'itemTaskBindings'})

    events.bind('jobs.job.update', 'item_tasks', _onJobSave)
    events.bind('data.process', 'item_tasks', _onUpload)

    info['apiRoot'].item_task = ItemTask()

    info['apiRoot'].item.route('POST', (':id', 'item_task_slicer_cli_description'),
                               runSlicerCliTasksDescriptionForItem)
    info['apiRoot'].item.route('PUT', (':id', 'item_task_slicer_cli_xml'),
                               configureItemTaskFromSlicerCliXml)
    info['apiRoot'].item.route('POST', (':id', 'item_task_json_description'),
                               runJsonTasksDescriptionForItem)
    info['apiRoot'].item.route('PUT', (':id', 'item_task_json_specs'),
                               configureItemTaskFromJson)
    info['apiRoot'].item.route('POST', (':id', 'item_task_celery'),
                               describeCeleryTaskItem)

    info['apiRoot'].folder.route('POST', (':id', 'item_task_slicer_cli_description'),
                                 runSlicerCliTasksDescriptionForFolder)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_slicer_cli_xml'),
                                 createItemTasksFromSlicerCliXml)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_json_description'),
                                 runJsonTasksDescriptionForFolder)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_json_specs'),
                                 createItemTasksFromJson)
    info['apiRoot'].folder.route('POST', (':id', 'item_task_celery'),
                                 celeryTaskDescriptionForFolder)


class ItemTasksPlugin(GirderPlugin):
    NPM_PACKAGE_NAME = '@girder/item_tasks'

    def load(self, info):
        getPlugin('jobs').load(info)
        getPlugin('worker').load(info)
        return load(info)
