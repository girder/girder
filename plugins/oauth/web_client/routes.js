import events from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('oauth', 'plugins/oauth/config');

import ConfigView from './views/ConfigView';
router.route('plugins/oauth/config', 'oauthConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
