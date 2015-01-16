// The same job status enum as the server.
girder.jobs_JobStatus = {
    INACTIVE: 0,
    QUEUED: 1,
    RUNNING: 2,
    SUCCESS: 3,
    ERROR: 4,
    CANCELED: 5,

    text: function (status) {
        if (status === this.INACTIVE) {
            return 'Inactive';
        }
        if (status === this.QUEUED) {
            return 'Queued';
        }
        if (status === this.RUNNING) {
            return 'Running';
        }
        if (status === this.ERROR) {
            return 'Error';
        }
        if (status === this.CANCELED) {
            return 'Canceled';
        }
        if (status === this.SUCCESS) {
            return 'Success';
        }
    }
};
