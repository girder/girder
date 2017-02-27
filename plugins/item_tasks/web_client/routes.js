import router from 'girder/router';
import events from 'girder/events';

import TaskListView from './views/TaskListView';
import TaskRunView from './views/TaskRunView';
import ItemModel from 'girder/models/ItemModel';

router.route('item_tasks', 'itemTaskList', () => {
    events.trigger('g:navigateTo', TaskListView);
    events.trigger('g:highlightItem', 'TasksView');
});

router.route('item_task/:id/run', (id) => {
    const item = new ItemModel({_id: id}).once('g:fetched', function () {
        events.trigger('g:navigateTo', TaskRunView, {
            model: item
        }, {
            renderNow: true
        });
    }, this).once('g:error', function () {
        router.navigate('item_tasks', {trigger: true});
    }, this);
    item.fetch();
});
