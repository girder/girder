/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('item_tags', 'plugins/item_tags/config');

import ConfigView from './views/ConfigView';
router.route('plugins/item_tags/config', 'itemTagsConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
