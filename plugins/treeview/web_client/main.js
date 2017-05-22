import './routes';

import { registerPluginNamespace } from 'girder/pluginUtils';

import * as treeview from './index';

registerPluginNamespace('treeview', treeview);
