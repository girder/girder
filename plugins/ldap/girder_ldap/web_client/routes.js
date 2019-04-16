/* eslint-disable import/first */

import events from '@girder/core/events';
import router from '@girder/core/router';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('ldap', 'plugins/ldap/config');

import ConfigView from './views/ConfigView';
router.route('plugins/ldap/config', 'ldapConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
