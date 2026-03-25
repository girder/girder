import './routes';

// Extends and overrides API
import './views/HeaderUserView';
import './views/AdminView';

import * as jobs from './index';

const { registerPluginNamespace } = girder.pluginUtils;

registerPluginNamespace('jobs', jobs);
