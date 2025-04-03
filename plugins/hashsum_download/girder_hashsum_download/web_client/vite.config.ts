import { resolve } from 'path';

import { defineConfig } from 'vite';
import istanbul from 'vite-plugin-istanbul';
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

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    pugPlugin(),
    istanbul({
      include: 'src/*',
      exclude: ['node_modules', 'test/'],
      extension: [ '.js', '.ts', '.vue' ],
      // requireEnv: true,
    }),
  ],
  build: {
    sourcemap: !process.env.SKIP_SOURCE_MAPS,
    lib: {
      entry: resolve(__dirname, 'main.js'),
      name: 'GirderPluginHashsumDownload',
      fileName: 'girder-plugin-hashsum-download',
    },
  },
});
