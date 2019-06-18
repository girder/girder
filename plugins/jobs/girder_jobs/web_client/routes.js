/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';

import JobModel from './models/JobModel';
import JobDetailsWidget from './views/JobDetailsWidget';
import JobListWidget from './views/JobListWidget';

router.route('job/:id', 'jobView', function (id) {
    var job = new JobModel({ _id: id }).once('g:fetched', function () {
        events.trigger('g:navigateTo', JobDetailsWidget, {
            job: job,
            renderImmediate: true
        });
    }, this).once('g:error', function () {
        router.navigate('collections', { trigger: true });
    }, this);
    job.fetch();
});

router.route('jobs/user/:id(/:view)', 'jobList', function (id, view) {
    events.trigger('g:navigateTo', JobListWidget, {
        filter: { userId: id },
        view: view,
        showGraphs: true,
        showFilters: true,
        showPageSizeSelector: true
    });
});

router.route('jobs(/:view)', 'allJobList', function (view) {
    events.trigger('g:navigateTo', JobListWidget, {
        allJobsMode: true,
        view: view,
        showGraphs: true,
        showFilters: true,
        showPageSizeSelector: true
    });
});
