/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('google_analytics', 'plugins/google_analytics/config');

import AbstractPluginConfigView from 'girder/views/layout/AbstractPluginConfigView';
router.route('plugins/google_analytics/config', 'googleAnalyticsConfig', function () {
    events.trigger('g:navigateTo', AbstractPluginConfigView, {
        pluginName: 'Google Analytics',
        description: 'To track pageviews in Girder, enter your Google Analytics tracking ID here.',
        settings: [
            {
                key: 'google_analytics.tracking_id',
                label: 'Google Analytics Tracking ID',
                placeholderText: '<required>'
            }
        ]
    });
});
