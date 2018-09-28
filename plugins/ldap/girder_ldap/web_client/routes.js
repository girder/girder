/* eslint-disable import/first */

import events from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('ldap', 'plugins/ldap/config');

import ConfigView from './views/ConfigView';
router.route('plugins/ldap/config', 'ldapConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
