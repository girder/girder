import router from 'girder/router';
import events from 'girder/events';

import JobModel from './models/JobModel';
import JobDetailsWidget from './views/JobDetailsWidget';
import JobListWidget from './views/JobListWidget';

router.route('job/:id', 'jobView', function (id) {
    var job = new JobModel({_id: id}).once('g:fetched', function () {
        events.trigger('g:navigateTo', JobDetailsWidget, {
            job: job,
            renderImmediate: true
        });
    }, this).once('g:error', function () {
        router.navigate('collections', {trigger: true});
    }, this);
    job.fetch();
});

router.route('jobs/user/:id', 'jobList', function (id) {
    events.trigger('g:navigateTo', JobListWidget, {
        filter: {userId: id}
    });
});
