import { events } from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/MiscFunctions';

exposePluginConfig('provenance', 'plugins/provenance/config');

import ConfigView from './views/ConfigView';
router.route('plugins/provenance/config', 'provenanceConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

