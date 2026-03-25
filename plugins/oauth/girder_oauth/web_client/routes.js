import ConfigView from './views/ConfigView';

const events = girder.events;
const router = girder.router;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('oauth', 'plugins/oauth/config');

router.route('plugins/oauth/config', 'oauthConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
