/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('sentry', 'plugins/sentry/config');

import ConfigView from './views/ConfigView';
router.route('plugins/sentry/config', 'SentryConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
