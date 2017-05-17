import 'jstree';
import 'jstree/dist/themes/default/style.css';

import { registerPluginNamespace } from 'girder/pluginUtils';

import * as treeview from './index';

registerPluginNamespace('treeview', treeview);
