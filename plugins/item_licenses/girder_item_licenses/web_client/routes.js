import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('item_licenses', 'plugins/item_licenses/config');

router.route('plugins/item_licenses/config', 'itemLicensesConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
