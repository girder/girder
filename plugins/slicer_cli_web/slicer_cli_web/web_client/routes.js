import ConfigView from './views/ConfigView';

const events = girder.events;
const router = girder.router;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('slicer_cli_web', 'plugins/slicer_cli_web/config');

router.route('plugins/slicer_cli_web/config', 'slicerCLIWebConfig', () => {
    events.trigger('g:navigateTo', ConfigView);
});
