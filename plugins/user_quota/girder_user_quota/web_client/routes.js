/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('user_quota', 'plugins/user_quota/config');

import ConfigView from './views/ConfigView';
router.route('plugins/user_quota/config', 'userQuotaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
