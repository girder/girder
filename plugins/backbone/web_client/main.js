import { registerPluginNamespace } from 'girder/pluginUtils';

import './rest';
import * as backbone from './index';

registerPluginNamespace('backbone', backbone);
