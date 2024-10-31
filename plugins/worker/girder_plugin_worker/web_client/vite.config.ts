import { resolve } from 'path';

import { defineConfig } from 'vite';
import { compileClient } from 'pug';

function pugPlugin() {
  return {
    name: 'pug',
    transform(src: string, id: string) {
      if (id.endsWith('.pug')) {
        return {
          code: `${compileClient(src, {filename: id})}\nexport default template`,
          map: null,
        };
      }
    },
  };
}

export default defineConfig({
  plugins: [
    pugPlugin(),
  ],
  build: {
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, 'main.js'),
      name: 'GirderPluginWorker',
      fileName: 'girder-plugin-worker',
    },
  }
});
