import { events } from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/MiscFunctions';

exposePluginConfig('user_quota', 'plugins/user_quota/config');

import ConfigView from './views/ConfigView';
router.route('plugins/user_quota/config', 'userQuotaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
