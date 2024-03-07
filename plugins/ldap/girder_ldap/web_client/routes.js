import ConfigView from './views/ConfigView';

const events = girder.events;
const router = girder.router;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('ldap', 'plugins/ldap/config');

router.route('plugins/ldap/config', 'ldapConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
