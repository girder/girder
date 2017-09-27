/* eslint-disable import/first */

import $ from 'jquery';
import _ from 'underscore';

import router from 'girder/router';
import events from 'girder/events';

import ItemModel from 'girder/models/ItemModel';
import FileModel from 'girder/models/FileModel';
import JobModel from 'girder_plugins/jobs/models/JobModel';

import TaskListView from './views/TaskListView';
import TaskRunView from './views/TaskRunView';

router.route('item_tasks', 'itemTaskList', () => {
    events.trigger('g:navigateTo', TaskListView);
    events.trigger('g:highlightItem', 'TasksView');
});

router.route('item_task/:id/run', (id, params) => {
    const itemTask = new ItemModel({_id: id});
    let job = null;
    let inputfile = null;
    const promises = [itemTask.fetch()];

    if (params.fromJob) {
        job = new JobModel({_id: params.fromJob});
        promises.push(job.fetch());
    }

    if (params.fileId) {
        inputfile = new FileModel({_id: params.fileId});
        promises.push(inputfile.fetch());
    }

    $.when(...promises).done(() => {
        let initialValues = {};

        if (params.fromJob && job.has('itemTaskBindings')) {
            initialValues = job.get('itemTaskBindings');
        }

        if (params.fileId) {
            let itemTaskSpec = itemTask.get('meta').itemTaskSpec;

            let fileInputSpecs = _.where(itemTaskSpec.inputs, {'type': 'file'});
            if (fileInputSpecs.length === 1) {
                let fileInputSpec = fileInputSpecs[0];
                initialValues.inputs = initialValues.inputs || {};
                initialValues.inputs[fileInputSpec.id] = {
                    mode: 'girder',
                    resource_type: 'file',
                    id: params.fileId,
                    fileName: inputfile.name()
                };
            }
        }

        events.trigger('g:navigateTo', TaskRunView, {
            model: itemTask,
            initialValues: initialValues
        }, {
            renderNow: true
        });
    }).fail(() => {
        router.navigate('item_tasks', {trigger: true, replace: true});
    });
});
