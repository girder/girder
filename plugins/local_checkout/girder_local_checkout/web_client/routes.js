/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('local_checkout', 'plugins/local_checkout/config');

import ConfigView from './views/ConfigView';
router.route('plugins/local_checkout/config', 'localCheckoutConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
