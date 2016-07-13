import './api';
import './routes';

import { exposePluginConfig } from 'girder/utilities/MiscFunctions';

exposePluginConfig('gravatar', 'plugins/gravatar/config');
