// import modules for side effects
import './routes';
import './views/ItemView';
import './views/CollectionView';
import './JobStatus';

// expose symbols under girder.plugins
import * as slicerCLIWeb from './index';

const { registerPluginNamespace } = girder.pluginUtils;
registerPluginNamespace('slicer_cli_web', slicerCLIWeb);
