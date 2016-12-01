import router from 'girder/router';
import events from 'girder/events';


import TaskListView from './views/TaskListView';
router.route('worker_tasks', 'workerTaskList', () => {
    events.trigger('g:navigateTo', TaskListView);
});
