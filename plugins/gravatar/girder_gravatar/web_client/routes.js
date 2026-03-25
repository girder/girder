import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('gravatar', 'plugins/gravatar/config');

router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
