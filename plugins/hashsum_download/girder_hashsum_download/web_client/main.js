/* eslint-disable import/first */

// Extends and overrides API
import './views/FileInfoWidget';

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('hashsum_download', 'plugins/hashsum_download/config');

import ConfigView from './views/ConfigView';
router.route('plugins/hashsum_download/config', 'hashsumDownloadConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
