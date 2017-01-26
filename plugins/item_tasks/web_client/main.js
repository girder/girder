import $ from 'jquery';
import _ from 'underscore';
import './routes';

import { getCurrentUser } from 'girder/auth';
import { wrap } from 'girder/utilities/PluginUtils';
import GlobalNavView from 'girder/views/layout/GlobalNavView';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import ItemView from 'girder/views/body/ItemView';
import { registerPluginNamespace } from 'girder/pluginUtils';

import * as itemTasks from 'girder_plugins/item_tasks';

registerPluginNamespace('item_tasks', itemTasks);

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
    this.once('g:rendered', function () {
        this.$('.g-item-actions-menu').prepend(itemMenuModTemplate({
            _: _,
            item: this.model,
            currentUser: getCurrentUser()
        }));
    }, this);
    return render.call(this);
});

import ConfigureTaskDialog from './views/ConfigureTaskDialog';
ItemView.prototype.events['click .g-configure-item-task'] = function () {
    if (!this.configureTaskDialog) {
        this.configureTaskDialog = new ConfigureTaskDialog({
            model: this.model,
            parentView: this,
            el: $('#g-dialog-container')
        });
    }
    this.configureTaskDialog.render();
};

import hierarchyMenuModTemplate from './templates/hierarchyMenuMod.pug';
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    this.$('.g-folder-actions-menu .dropdown-header').after(hierarchyMenuModTemplate({
        _: _,
        parentType: this.parentModel.get('_modelType'),
        currentUser: getCurrentUser()
    }));
    return this;
});

import ConfigureTasksDialog from './views/ConfigureTasksDialog';
HierarchyWidget.prototype.events['click .g-create-docker-tasks'] = function () {
    if (!this.configureTasksDialog) {
        this.configureTasksDialog = new ConfigureTasksDialog({
            model: this.parentModel,
            parentView: this,
            el: $('#g-dialog-container')
        });
    }
    this.configureTasksDialog.render();
};

// Show task inputs and outputs on job details view
import JobDetailsInfoView from './views/JobDetailsInfoView';
import taskItemLinkTemplate from './templates/taskItemLink.pug';
/* global girder */
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
