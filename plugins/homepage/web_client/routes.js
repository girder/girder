import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('homepage', 'plugins/homepage/config');

import ConfigView from './views/ConfigView';
router.route('plugins/homepage/config', 'homepageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
