/* eslint-disable import/first */

import events from '@girder/core/events';
import router from '@girder/core/router';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('oauth', 'plugins/oauth/config');

import ConfigView from './views/ConfigView';
router.route('plugins/oauth/config', 'oauthConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
