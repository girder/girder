import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('treeview', 'plugins/treeview/config');

import ConfigView from './views/ConfigView';
router.route('plugins/treeview/config', 'treeviewConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
