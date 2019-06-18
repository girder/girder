/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('autojoin', 'plugins/autojoin/config');

import ConfigView from './views/ConfigView';
router.route('plugins/autojoin/config', 'autojoinConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
