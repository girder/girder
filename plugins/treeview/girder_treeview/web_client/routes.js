/* eslint-disable import/first */
import { exposePluginConfig } from 'girder/utilities/PluginUtils';
import events from 'girder/events';
import router from 'girder/router';

exposePluginConfig('treeview', 'plugins/treeview/config');

import ConfigView from './views/ConfigView';
router.route('plugins/treeview/config', 'treeviewConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
