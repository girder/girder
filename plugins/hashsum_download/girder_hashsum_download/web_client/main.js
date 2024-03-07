
import './views/FileInfoWidget';
import ConfigView from './views/ConfigView';

const router = girder.router;
const events = girder.events;
const { exposePluginConfig } = girder.utilities.PluginUtils;

exposePluginConfig('hashsum_download', 'plugins/hashsum_download/config');

router.route('plugins/hashsum_download/config', 'hashsumDownloadConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
