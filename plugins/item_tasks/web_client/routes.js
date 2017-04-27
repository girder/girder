import router from 'girder/router';
import events from 'girder/events';

import TaskListView from './views/TaskListView';
import TaskRunView from './views/TaskRunView';
import ItemModel from 'girder/models/ItemModel';
import JobModel from 'girder_plugins/jobs/models/JobModel';

router.route('item_tasks', 'itemTaskList', () => {
    events.trigger('g:navigateTo', TaskListView);
    events.trigger('g:highlightItem', 'TasksView');
});

router.route('item_task/:id/run', (id, params) => {
    const item = new ItemModel({_id: id});
    let job = null;
    const promises = [item.fetch()];

    if (params.fromJob) {
        job = new JobModel({_id: params.fromJob});
        promises.push(job.fetch());
    }

    $.when.apply($, promises).done(() => {
        events.trigger('g:navigateTo', TaskRunView, {
            model: item,
            initialValues: job && job.get('itemTaskBindings')
        }, {
            renderNow: true
        });
    }).fail(() => {
        router.navigate('item_tasks', {trigger: true});
    });
});
