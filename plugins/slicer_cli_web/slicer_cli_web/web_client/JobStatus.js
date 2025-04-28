const events = girder.events;

// g:appload.before runs after all plugin static files have been loaded
events.on('g:appload.before', () => {
    const JobStatus = girder.plugins.jobs.JobStatus;
    const jobPluginIsCancelable = JobStatus.isCancelable;
    JobStatus.isCancelable = function (job) {
        if (job.get('type').startsWith('slicer_cli_web_batch')) {
            return ![JobStatus.CANCELED, JobStatus.WORKER_CANCELING || 824,
                JobStatus.SUCCESS, JobStatus.ERROR].includes(job.get('status'));
        }
        return jobPluginIsCancelable(job);
    };
});
