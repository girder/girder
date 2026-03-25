import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('user_quota', 'plugins/user_quota/config');

router.route('plugins/user_quota/config', 'userQuotaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
