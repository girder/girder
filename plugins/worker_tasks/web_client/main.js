import $ from 'jquery';
import './routes';

import { wrap } from 'girder/utilities/PluginUtils';
import GlobalNavView from 'girder/views/layout/GlobalNavView';

// Add a new global nav item for running analyses
wrap(GlobalNavView, 'initialize', function (initialize) {
    initialize.apply(this, arguments);

    this.defaultNavItems.push({
        name: 'Tasks',
        icon: 'icon-cog-alt',
        target: 'worker_tasks'
    });
});

// Show task inputs and outputs on job details view
import JobDetailsInfoView from './views/JobDetailsInfoView';
wrap(girder.plugins.jobs.views.JobDetailsWidget, 'render', function (render) {
    render.call(this);

    if (this.job.has('workerTaskBindings')) {
        var el = $('<div/>', {class: 'g-worker-tasks-job-info-container'}).appendTo(this.$el);

        new JobDetailsInfoView({
            el,
            parentView: this,
            model: this.job
        }).render();
    }
});
