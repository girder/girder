import path, { resolve } from 'path';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { compileClient } from 'pug';
import dts from 'vite-plugin-dts';
import inject from "@rollup/plugin-inject";
import { viteStaticCopy } from 'vite-plugin-static-copy';

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

let buildOpts = {};
const plugins: any[] = [];
let outDir = 'dist';

if (process.env.BUILD_LIB) {
  buildOpts = {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'GirderCore',
      fileName: 'girder-core',
    }
  };

  plugins.push(dts({
    insertTypesEntry: true,
    exclude: ['node_modules/**', 'dist-lib/**'],
  }));

  outDir = 'dist-lib';
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    inject({
      $: 'jquery',
      jQuery: 'jquery',
      exclude: 'src/**/*.pug',
    }),
    vue(),
    pugPlugin(),
    viteStaticCopy({
      targets: [
        {
          src: path.resolve(__dirname, './src') + '/[!.]*',
          dest: './src',
        },
      ],
    }).filter((config) => config.apply === 'build'), // Don't copy sources for dev server
    ...plugins,
  ],
  resolve: {
    alias: {
      '@girder/core': resolve(__dirname, 'src'),
    }
  },
  build: {
    sourcemap: !process.env.SKIP_SOURCE_MAPS,
    outDir,
    ...buildOpts,
  },
});
