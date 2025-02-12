import JobStatus from '@girder/jobs/JobStatus';

const jobPluginIsCancelable = JobStatus.isCancelable;
JobStatus.isCancelable = function (job) {
    if (['assetstore_import', 'folder_move'].includes(job.get('type'))) {
        return ![JobStatus.CANCELED, JobStatus.SUCCESS, JobStatus.ERROR].includes(job.get('status'));
    }
    return jobPluginIsCancelable(job);
};
