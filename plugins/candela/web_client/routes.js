/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('candela', 'plugins/candela/config');

import ConfigView from './views/ConfigView';
router.route('plugins/candela/config', 'candelaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
