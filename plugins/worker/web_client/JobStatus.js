// Since plugins are not dynamically linked against other plugin libraries,
// we have to modify the runtime global JobStatus, rather than importing it
// here statically, which would only modify a local copy.

/*global girder*/
girder.plugins.jobs.JobStatus.registerStatus({
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
        icon: 'icon-cancel',
        color: '#f89406'
    }
});
