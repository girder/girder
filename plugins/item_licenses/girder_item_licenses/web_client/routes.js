/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('item_licenses', 'plugins/item_licenses/config');

import ConfigView from './views/ConfigView';
router.route('plugins/item_licenses/config', 'itemLicensesConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
