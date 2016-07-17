import router from 'girder/router';
import { events } from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/MiscFunctions';

exposePluginConfig('vega', 'plugins/vega/config');

import ConfigView from './views/ConfigView';
router.route('plugins/vega/config', 'vegaConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
