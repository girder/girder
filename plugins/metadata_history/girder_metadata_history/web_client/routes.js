/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('metadata_history', 'plugins/metadata_history/config');

import ConfigView from './views/ConfigView';
router.route('plugins/metadata_history/config', 'metadataHistoryConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
