/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('worker', 'plugins/worker/config');

import AbstractPluginConfigView from 'girder/views/layout/AbstractPluginConfigView';
router.route('plugins/worker/config', 'workerConfig', function () {
    events.trigger('g:navigateTo', AbstractPluginConfigView, {
        pluginName: 'Remote worker',
        description: 'Configure how Girder should connect to the celery worker.',
        settings: [
            {
                key: 'worker.broker',
                label: 'Celery broker URL'
            },
            {
                key: 'worker.backend',
                label: 'Celery backend URL'
            },
            {
                key: 'worker.api_url',
                label: 'Alternative Girder API URL',
                placeholderText: 'default: auto-detected'
            }
        ]
    });
});
