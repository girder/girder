import router from 'girder/router';
import events from 'girder/events';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

import ConfigView from './views/ConfigView';

exposePluginConfig('{{ cookiecutter.plugin_name }}', 'plugins/{{ cookiecutter.plugin_name }}/config');

router.route('plugins/{{ cookiecutter.plugin_name }}/config', '{{ cookiecutter.plugin_camel_case }}Config', function () {
    events.trigger('g:navigateTo', ConfigView);
});
