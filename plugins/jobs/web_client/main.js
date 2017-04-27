import './routes';

// Extends and overrides API
import './views/HeaderUserView';
import './views/AdminView';

import { registerPluginNamespace } from 'girder/pluginUtils';
import * as jobs from './index';

registerPluginNamespace('jobs', jobs);
