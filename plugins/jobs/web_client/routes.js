import router from 'girder/router';
import { events } from 'girder/events';

import JobModel from './models/JobModel';

import jobs_JobDetailsWidget from './views/JobDetailsWidget';
router.route('job/:id', 'jobView', function (id) {
    var job = new JobModel({_id: id}).once('g:fetched', function () {
        events.trigger('g:navigateTo', jobs_JobDetailsWidget, {
            job: job,
            renderImmediate: true
        });
    }, this).once('g:error', function () {
        router.navigate('collections', {trigger: true});
    }, this).fetch();
});

import jobs_JobListWidget from './views/JobListWidget';
router.route('jobs/user/:id', 'jobList', function (id) {
    events.trigger('g:navigateTo', jobs_JobListWidget, {
        filter: {userId: id}
    });
});
