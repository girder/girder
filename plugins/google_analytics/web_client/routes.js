import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('google_analytics', 'plugins/google_analytics/config');

import ConfigView from './views/ConfigView';
router.route('plugins/google_analytics/config', 'googleAnalyticsConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
