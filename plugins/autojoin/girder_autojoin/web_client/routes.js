import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('autojoin', 'plugins/autojoin/config');

router.route('plugins/autojoin/config', 'autojoinConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
