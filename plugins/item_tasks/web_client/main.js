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
        target: 'item_tasks'
    });
});

import itemMenuModTemplate from './templates/itemMenuMod.pug';
wrap(ItemView, 'render', function (render) {
    if (_.has(this.model.get('meta'), 'itemTaskSpec')) {
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
import taskItemLinkTemplate from './templates/taskItemLink.pug';
wrap(girder.plugins.jobs.views.JobDetailsWidget, 'render', function (render) {
    render.call(this);

    if (this.job.has('itemTaskId')) {
        this.$('.g-job-info-value[property="title"]').html(taskItemLinkTemplate({
            itemId: this.job.get('itemTaskId'),
            title: this.job.get('title')
        }));
    }
    if (this.job.has('itemTaskBindings')) {
        var el = $('<div/>', {class: 'g-item-tasks-job-info-container'}).prependTo(this.$el);

        new JobDetailsInfoView({
            el,
            parentView: this,
            model: this.job
        }).render();
    }
});
