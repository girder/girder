import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('celery_jobs', 'plugins/celery_jobs/config');

import ConfigView from './views/ConfigView';
router.route('plugins/celery_jobs/config', 'celeryJobsConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
