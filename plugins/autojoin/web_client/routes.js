import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('autojoin', 'plugins/autojoin/config');

import ConfigView from './views/ConfigView';
router.route('plugins/autojoin/config', 'autojoinConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
