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
          code: `${compileClient(src, { filename: id, compileDebug: false })}\nexport default template`,
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
      include: ['**/*.js', '**/*.ts', '**/*.vue', '**/*.pug'],
      exclude: ['node_modules/**', 'dist/**'],
      extension: ['.js', '.ts', '.vue', '.pug'],
      requireEnv: false,
      // Only instrument when the test harness asks for coverage.
      forceBuildInstrument: !!process.env.GIRDER_TEST_COVERAGE,
    }),
  ],
  build: {
    sourcemap: !process.env.SKIP_SOURCE_MAPS,
    lib: {
      entry: resolve(import.meta.dirname, 'main.js'),
      name: 'GirderPluginItemLicenses',
      fileName: 'girder-plugin-item-licenses',
    },
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'style.css';
          }
          return '[name].[ext]';
        },
      },
    },
  },
});
