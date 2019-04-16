/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('homepage', 'plugins/homepage/config');

import ConfigView from './views/ConfigView';
router.route('plugins/homepage/config', 'homepageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
