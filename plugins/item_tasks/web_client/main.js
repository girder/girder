/* eslint-disable import/first, import/order */

import $ from 'jquery';
import _ from 'underscore';

import { getCurrentUser } from 'girder/auth';
import { wrap } from 'girder/utilities/PluginUtils';
import GlobalNavView from 'girder/views/layout/GlobalNavView';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import ItemView from 'girder/views/body/ItemView';
import { registerPluginNamespace } from 'girder/pluginUtils';
import JobModel from '@girder/jobs/models/JobModel';
import * as itemTasks from './index';
import router from 'girder/router';

import './routes';

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
import itemInfoModTemplate from './templates/itemInfoMod.pug';
wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        this.$('.g-item-actions-menu').prepend(itemMenuModTemplate({
            _,
            item: this.model,
            currentUser: getCurrentUser()
        }));

        if (this.model.get('createdByJob')) {
            var job = new JobModel({_id: this.model.get('createdByJob')});
            job.fetch({ignoreError: true}).done(() => {
                this.$('.g-item-info').append(itemInfoModTemplate({
                    job
                }));
            });
        }
    }, this);
    return render.call(this);
});

// "Configure Task" button in Actions drop down menu
import ConfigureTasksDialog from './views/ConfigureTasksDialog';
ItemView.prototype.events['click .g-configure-item-task'] = function () {
    if (!this.configureTaskDialog) {
        this.configureTaskDialog = new ConfigureTasksDialog({
            model: this.model,
            parentView: this,
            el: $('#g-dialog-container')
        });
    }
    this.configureTaskDialog.render();
};

// "Select Task" button in Actions drop down menu
import SelectSingleFileTaskWidget from './views/SelectSingleFileTaskWidget';
ItemView.prototype.events['click .g-select-item-task'] = function (e) {
    new SelectSingleFileTaskWidget({
        el: $('#g-dialog-container'),
        parentView: this,
        item: this.model
    }).once('g:selected', function (params) {
        let item = params.item;
        let task = params.task;

        router.navigate(`item_task/${task.id}/run?itemId=${item.id}`, {trigger: true});
    }, this).render();
};

import hierarchyMenuModTemplate from './templates/hierarchyMenuMod.pug';
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    this.$('.g-folder-actions-menu .dropdown-header').after(hierarchyMenuModTemplate({
        parentType: this.parentModel.get('_modelType'),
        currentUser: getCurrentUser()
    }));
    return this;
});

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
import JobDetailsWidget from '@girder/jobs/views/JobDetailsWidget';
import JobDetailsInfoView from './views/JobDetailsInfoView';
wrap(JobDetailsWidget, 'render', function (render) {
    render.call(this);

    if (this.job.has('itemTaskBindings')) {
        new JobDetailsInfoView({
            className: 'g-item-tasks-job-info-container',
            parentView: this,
            model: this.job
        })
            .render()
            .$el.insertBefore(this.$('.g-job-info-key[property="log"]'));
    }
});
