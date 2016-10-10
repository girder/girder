import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('item_licenses', 'plugins/item_licenses/config');

import ConfigView from './views/ConfigView';
router.route('plugins/item_licenses/config', 'itemLicensesConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
