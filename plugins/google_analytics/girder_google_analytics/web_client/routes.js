import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('google_analytics', 'plugins/google_analytics/config');

router.route('plugins/google_analytics/config', 'googleAnalyticsConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
