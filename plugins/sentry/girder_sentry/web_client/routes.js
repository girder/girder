import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('sentry', 'plugins/sentry/config');

router.route('plugins/sentry/config', 'SentryConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
