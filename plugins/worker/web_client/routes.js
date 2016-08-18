import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('worker', 'plugins/worker/config');

import ConfigView from './views/ConfigView';
router.route('plugins/worker/config', 'workerConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
