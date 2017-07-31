import JobStatus from 'girder_plugins/jobs/JobStatus';

JobStatus.registerStatus({
    WORKER_FETCHING_INPUT: {
        value: 820,
        text: 'Fetching input',
        icon: 'icon-download',
        color: '#89d2e2'
    },
    WORKER_CONVERTING_INPUT: {
        value: 821,
        text: 'Converting input',
        icon: 'icon-shuffle',
        color: '#92f5b5'
    },
    WORKER_CONVERTING_OUTPUT: {
        value: 822,
        text: 'Converting output',
        icon: 'icon-shuffle',
        color: '#92f5b5'
    },
    WORKER_PUSHING_OUTPUT: {
        value: 823,
        text: 'Pushing output',
        icon: 'icon-upload',
        color: '#89d2e2'
    },
    WORKER_CANCELING: {
        value: 824,
        text: 'Canceling',
        icon: 'icon-spin3 animate-spin',
        color: '#f89406'
    }
});

const jobPluginIsCancelable = JobStatus.isCancelable;
JobStatus.isCancelable = function (job) {
    const handler = job.get('handler');
    if (handler === 'worker_handler') {
        return [JobStatus.CANCELED, JobStatus.WORKER_CANCELING,
            JobStatus.SUCCESS, JobStatus.ERROR].indexOf(job.get('status')) === -1;
    } else if (handler === 'celery_handler') {
        // Currently celery_handler jobs can't be cancelled in the running state
        return [JobStatus.RUNNING, JobStatus.CANCELED, JobStatus.WORKER_CANCELING,
            JobStatus.SUCCESS, JobStatus.ERROR].indexOf(job.get('status')) === -1;
    }

    return jobPluginIsCancelable(job);
};
