const events = girder.events;

// Ensure this code runs after all plugin static files have been loaded
events.on('g:appload.before', () => {
    const JobStatus = girder.plugins.jobs.JobStatus;
    const jobPluginIsCancelable = JobStatus.isCancelable;
    JobStatus.isCancelable = function (job) {
        if (['assetstore_import', 'folder_move'].includes(job.get('type'))) {
            return ![JobStatus.CANCELED, JobStatus.SUCCESS, JobStatus.ERROR].includes(job.get('status'));
        }
        return jobPluginIsCancelable(job);
    };
});
