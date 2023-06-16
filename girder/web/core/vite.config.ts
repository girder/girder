import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import istanbul from 'vite-plugin-istanbul';
import path, { resolve } from 'path';
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

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    inject({
      $: 'jquery',
      jQuery: 'jquery',
      exclude: 'src/**/*.pug',
    }),
    dts({
      insertTypesEntry: true,
      exclude: ['node_modules/**', 'dist/**'],
    }),
    vue(),
    pugPlugin(),
    istanbul({
      include: 'src/*',
      exclude: ['node_modules', 'test/', 'dist/'],
      extension: [ '.js', '.ts', '.vue' ],
      // requireEnv: true,
    }),
    viteStaticCopy({
      targets: [
        {
          src: path.resolve(__dirname, './src') + '/[!.]*',
          dest: './src',
        },
      ],
    }).filter((config) => config.apply === 'build'), // Don't copy sources for dev server
  ],
  resolve: {
    alias: {
      '@girder/core': resolve(__dirname, 'src'),
    }
  },
  build: {
    sourcemap: true,
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'GirderCore',
      fileName: 'girder-core',
    },
  },
});
