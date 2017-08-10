/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('provenance', 'plugins/provenance/config');

import AbstractPluginConfigView from 'girder/views/layout/AbstractPluginConfigView';
router.route('plugins/provenance/config', 'provenanceConfig', function () {
    events.trigger('g:navigateTo', AbstractPluginConfigView, {
        pluginName: 'Provenance tracker',
        description: 'All additions and edits to tracked resources will be recorded with information about who changed the resource, when they changed it, and how it was changed.',
        settings: [
            {
                key: 'provenance.resources',
                label: 'Tracked Provenance Resources',
                description: 'Items are always tracked.  To track other resources, list them in a comma-separated list.  For example, to track items, folders, and collections, set this to "folder, collection".'
            }
        ]
    });
});
