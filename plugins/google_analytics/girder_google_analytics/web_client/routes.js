/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('google_analytics', 'plugins/google_analytics/config');

import ConfigView from './views/ConfigView';
router.route('plugins/google_analytics/config', 'googleAnalyticsConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
