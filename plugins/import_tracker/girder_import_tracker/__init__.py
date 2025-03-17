import time
from pathlib import Path

from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from girder import plugin
from girder.api.describe import autoDescribeRoute
from girder.api.rest import boundHandler
from girder.constants import AccessType
from girder.models.file import File
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext

from .models import AssetstoreImport, ImportTrackerCancelError
from .rest import getImport, listAllImports, listImports, moveFolder


def wrapImportData(assetstoreResource):
    baseImportData = assetstoreResource.importData
    baseImportData.description.param(
        'excludeExisting',
        'If true, then a file with an import path that is already in the '
        'system is not imported, even if it is not in the destination '
        'hierarchy.', dataType='boolean', required=False, default=False)

    @boundHandler(ctx=assetstoreResource)
    @autoDescribeRoute(baseImportData.description)
    def importDataWrapper(
            self, assetstore, importPath, destinationId, destinationType,
            progress, leafFoldersAsItems, fileIncludeRegex, fileExcludeRegex,
            excludeExisting, **kwargs):
        # We don't actually wrap importData, as it would be excessive
        # monkey-patching to make the import trackable and cancelable.
        user = self.getCurrentUser()
        parent = ModelImporter.model(destinationType).load(
            destinationId, user=user, level=AccessType.ADMIN, exc=True)

        # Capture any additional parameters passed to route
        extraParams = kwargs.get('params', {})

        params = {
            'destinationId': destinationId,
            'destinationType': destinationType,
            'importPath': importPath,
            'leafFoldersAsItems': str(leafFoldersAsItems).lower(),
            'progress': str(progress).lower(),
            **extraParams
        }

        if fileIncludeRegex:
            params['fileIncludeRegex'] = fileIncludeRegex
        if fileExcludeRegex:
            params['fileExcludeRegex'] = fileExcludeRegex
        if excludeExisting:
            params['excludeExisting'] = str(excludeExisting).lower()

        importRecord = AssetstoreImport().createAssetstoreImport(assetstore, params)

        job = Job().createJob(
            title='Import from %s : %s' % (assetstore['name'], importPath),
            type='assetstore_import',
            public=False,
            user=user,
            kwargs=params,
        )
        job = Job().updateJob(job, '%s - Starting import from %s : %s\n' % (
            time.strftime('%Y-%m-%d %H:%M:%S'),
            assetstore['name'], importPath,
        ), status=JobStatus.RUNNING)

        try:
            with ProgressContext(progress, user=user, title='Importing data') as ctx:
                try:
                    jobRec = {
                        'id': str(job['_id']),
                        'count': 0,
                        'skip': 0,
                        'lastlog': time.time(),
                        'logcount': 0,
                    }
                    self._model.importData(
                        assetstore, parent=parent, parentType=destinationType,
                        params={
                            **params,
                            '_job': jobRec,
                        },
                        progress=ctx, user=user,
                        leafFoldersAsItems=leafFoldersAsItems)
                    # TODO: if excludeExisting, then find any folders in the
                    # destination that contain no items or folders and remove
                    # them.
                    success = True
                    Job().updateJob(job, '%s - Finished.  Checked %d, skipped %d\n' % (
                        time.strftime('%Y-%m-%d %H:%M:%S'),
                        jobRec['count'], jobRec['skip'],
                    ), status=JobStatus.SUCCESS)
                except ImportTrackerCancelError:
                    Job().updateJob(job, '%s - Canceled' % (
                        time.strftime('%Y-%m-%d %H:%M:%S'),
                    ))
                    success = 'canceled'
        except Exception as exc:
            Job().updateJob(job, '%s - Failed with %s\n' % (
                time.strftime('%Y-%m-%d %H:%M:%S'),
                exc,
            ), status=JobStatus.ERROR)
            success = False

        importRecord = AssetstoreImport().markEnded(importRecord, success)
        return importRecord

    for key in {'accessLevel', 'description', 'requiredScopes'}:
        setattr(importDataWrapper, key, getattr(baseImportData, key))

    assetstoreResource.importData = importDataWrapper
    assetstoreResource.removeRoute('POST', (':id', 'import'))
    assetstoreResource.route('POST', (':id', 'import'), assetstoreResource.importData)


def wrapShouldImportFile():
    baseShouldImportFile = AbstractAssetstoreAdapter.shouldImportFile

    def shouldImportFileWrapper(self, path, params):
        jobRec = params.get('_job')
        job = None
        if jobRec:
            job = Job().load(jobRec['id'], force=True, includeLog=False)
        if job:
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


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'import_tracker'

    def load(self, info):
        plugin.getPlugin('jobs').load(info)
        ModelImporter.registerModel(
            'assetstoreImport', AssetstoreImport, 'import_tracker'
        )

        info['apiRoot'].assetstore.route('GET', (':id', 'imports'), listImports)
        info['apiRoot'].assetstore.route('GET', ('all_imports',), listAllImports)
        info['apiRoot'].assetstore.route('GET', ('import', ':id'), getImport)
        wrapShouldImportFile()
        wrapImportData(info['apiRoot'].assetstore)

        info['apiRoot'].folder.route('PUT', (':id', 'move'), moveFolder)
        plugin.registerPluginStaticContent(
            plugin='import-tracker',
            css=['style.css'],
            js=['girder-plugin-import-tracker.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot']
        )
