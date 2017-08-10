/* eslint-disable import/first */

import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('gravatar', 'plugins/gravatar/config');

import AbstractPluginConfigView from 'girder/views/layout/AbstractPluginConfigView';
router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    events.trigger('g:navigateTo', AbstractPluginConfigView, {
        pluginName: 'Gravatar portraits',
        description: 'The default image can be a URL, or one of the special defaults mentioned [here](https://en.gravatar.com/site/implement/images/).',
        settings: [
            {
                key: 'gravatar.default_image',
                label: 'Default image'
            }
        ]
    });
});
