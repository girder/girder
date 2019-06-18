/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('gravatar', 'plugins/gravatar/config');

import ConfigView from './views/ConfigView';
router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
