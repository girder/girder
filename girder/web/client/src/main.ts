import * as girder from '@girder/core';
import '@girder/core/style.css';

import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.css', { eager: true });
const modules = import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.js', { eager: true });
girder.loadPlugins(modules as Record<string, girder.GirderPlugin>, girder);

girder.initializeDefaultApp();
