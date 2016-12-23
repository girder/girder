import $ from 'jquery';
import _ from 'underscore';
import './routes';

import { wrap } from 'girder/utilities/PluginUtils';
import GlobalNavView from 'girder/views/layout/GlobalNavView';
import ItemView from 'girder/views/body/ItemView';

// Add a new global nav item for running analyses
wrap(GlobalNavView, 'initialize', function (initialize) {
    initialize.apply(this, arguments);

    this.defaultNavItems.push({
        name: 'Tasks',
        icon: 'icon-cog-alt',
        target: 'worker_tasks'
    });
});

import itemMenuModTemplate from './templates/itemMenuMod.pug';
wrap(ItemView, 'render', function (render) {
    if (_.has(this.model.get('meta'), 'workerTaskSpec')) {
        this.once('g:rendered', function () {
            this.$('.g-item-actions-menu').prepend(itemMenuModTemplate({
                item: this.model
            }));
        }, this);
    }
    return render.call(this);
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
