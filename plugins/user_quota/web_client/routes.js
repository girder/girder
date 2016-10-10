import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('user_quota', 'plugins/user_quota/config');

import ConfigView from './views/ConfigView';
router.route('plugins/user_quota/config', 'userQuotaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
