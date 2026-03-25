import ConfigView from './views/ConfigView';
import TaskStatusView from './views/taskStatusView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('worker', 'plugins/worker/config');

router.route('plugins/worker/config', 'workerConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

router.route('plugins/worker/task/status', 'workerTaskStatus', function () {
    events.trigger('g:navigateTo', TaskStatusView);
});
