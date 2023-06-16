/* eslint-disable import/first */

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('homepage', 'plugins/homepage/config');

import ConfigView from './views/ConfigView';
router.route('plugins/homepage/config', 'homepageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
