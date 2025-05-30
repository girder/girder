import time
from girder import events

from girder.models.file import File
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job
from girder_worker import GirderWorkerPluginABC

from .models import AssetstoreImport, ImportTrackerCancelError


def wrapShouldImportFile():
    baseShouldImportFile = AbstractAssetstoreAdapter.shouldImportFile

    def shouldImportFileWrapper(self, path, params):
        jobRec = params.get('_job')
        job = None
        if jobRec:
            job = Job().load(jobRec['id'], force=True, includeLog=False)
            if job['status'] == JobStatus.CANCELED:
                raise ImportTrackerCancelError()
            if time.time() - jobRec['lastlog'] > 10:
                Job().updateJob(
                    job,
                    log='%s - Checked %d, skipped %d; checking %s\n' % (
                        time.strftime('%Y-%m-%d %H:%M:%S'),
                        jobRec['count'], jobRec['skip'], path),
                    overwrite=(jobRec['logcount'] > 1000))
                if jobRec['logcount'] > 1000:
                    jobRec['logcount'] = 0
                jobRec['logcount'] += 1
                jobRec['lastlog'] = time.time()
        result = True
        if params.get('excludeExisting'):
            idx1 = ([('assetstoreId', 1), ('path', 1)], {})
            idx2 = ([('assetstoreId', 1), ('s3Key', 1)], {})
            if idx1 not in File()._indices:
                File().ensureIndex(idx1)
            if idx2 not in File()._indices:
                File().ensureIndex(idx2)
            if File().findOne({
                'assetstoreId': self.assetstore['_id'],
                '$or': [{'path': path}, {'s3Key': path}],
                'imported': True
            }):
                result = False
        if result:
            result = baseShouldImportFile(self, path, params)
        if jobRec:
            if not result:
                jobRec['skip'] += 1
            else:
                jobRec['count'] += 1
        return result

    AbstractAssetstoreAdapter.shouldImportFile = shouldImportFileWrapper


def createImportRecord(event: events.Event):
    info = event.info
    path = info['params']['importPath']
    record_data = {
        'destinationId': info['parent']['_id'],
        'destinationType': info['parentType'],
        'importPath': path,
        'leafFoldersAsItems': str(info['params'].get('leafFoldersAsItems', False)).lower(),
        'progress': str(info['progress']).lower(),
        **info['params']
    }

    job = Job().createJob(
        title='Import from %s : %s' % (info['assetstore']['name'], path),
        type='assetstore_import',
        public=False,
        user=info['user'],
        kwargs=info['params'],
    )
    job = Job().updateJob(job, '%s - Starting import from %s : %s\n' % (
        time.strftime('%Y-%m-%d %H:%M:%S'),
        info['assetstore']['name'], path,
    ), status=JobStatus.RUNNING)

    # We mutate the params dict in-place as a side-effect, unfortunately.
    info['params']['_job'] = {
        'id': str(job['_id']),
        'count': 0,
        'skip': 0,
        'lastlog': time.time(),
        'logcount': 0,
    }

    if 'fileIncludeRegex' in info['params']:
        record_data['fileIncludeRegex'] = info['params']['fileIncludeRegex']
    if 'fileExcludeRegex' in info['params']:
        record_data['fileExcludeRegex'] = info['params']['fileExcludeRegex']
    if 'excludeExisting' in info['params']:
        record_data['excludeExisting'] = str(info['params']['excludeExisting']).lower()

    import_record = AssetstoreImport().createAssetstoreImport(info['assetstore'], record_data)
    event.addResponse({'importRecord': import_record})


def finalizeImportRecord(event: events.Event):
    job_info = event.info['params']['_job']
    job = Job().load(job_info['id'], force=True, includeLog=False)

    if 'exception' in event.info:
        exc = event.info['exception']
        if isinstance(exc, ImportTrackerCancelError):
            success = 'canceled'
            Job().updateJob(job, '%s - Canceled\n' % time.strftime('%Y-%m-%d %H:%M:%S'))
        else:
            success = False
            Job().updateJob(job, '%s - Failed with %s' % (
                time.strftime('%Y-%m-%d %H:%M:%S'),
                exc,
            ), status=JobStatus.ERROR)
    else:
        success = True
        Job().updateJob(job, '%s - Finished.  Checked %d, skipped %d\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'),
            job_info['count'], job_info['skip'],
        ), status=JobStatus.SUCCESS)

    pre_event = event.info['pre_event']
    for response in pre_event.responses:
        if isinstance(response, dict) and 'importRecord' in response:
            AssetstoreImport().markEnded(response['importRecord'], success)
            break


class ImportTrackerWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        wrapShouldImportFile()

        events.bind('assetstore_import.before', 'import_tracker', createImportRecord)
        events.bind('assetstore_import.after', 'import_tracker', finalizeImportRecord)
        events.bind('assetstore_import.error', 'import_tracker', finalizeImportRecord)
