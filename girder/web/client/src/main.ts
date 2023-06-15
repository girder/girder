import { girder, type GirderPlugin } from '@girder/core';
import '@girder/core/style.css';

import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.css', { eager: true });
const modules = import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.js', { eager: true });
girder.loadPlugins(modules as Record<string, GirderPlugin>, girder);

girder.initializeDefaultApp();
