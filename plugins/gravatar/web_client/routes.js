import router from 'girder/router';
import { events } from 'girder/events';

import ConfigView from './views/ConfigView';
router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
