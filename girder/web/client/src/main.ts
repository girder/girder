import { girder, type GirderPackageInfo } from '@girder/core';
import '@girder/core/style.css';

declare global {
  interface Window {
    girder: typeof girder;
  }
}
window.girder = girder;

import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.css', { eager: true });
const packageInfo = import.meta.glob('/node_modules/**/girder-plugin-*/package.json', { eager: true });
const modules = import.meta.glob('/node_modules/**/girder-plugin-*/dist/*.js');
await girder.loadPlugins(modules, packageInfo as Record<string, GirderPackageInfo>);

girder.initializeDefaultApp();
