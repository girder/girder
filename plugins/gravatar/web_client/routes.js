import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('gravatar', 'plugins/gravatar/config');

import ConfigView from './views/ConfigView';
router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
