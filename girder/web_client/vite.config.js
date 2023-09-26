import { defineConfig } from 'vite'
import { resolve } from 'path'
import vue from '@vitejs/plugin-vue'
import inject from "@rollup/plugin-inject";
import { compileClient } from 'pug'

function pug() {
  return {
    name: 'pug',
    transform(src, id) {
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
      exclude: '**/*.pug',
    }),
    vue(),
    pug(),
  ],
  build: {
    outDir: resolve(__dirname, 'static/built'),
    lib: {
      entry: resolve(__dirname, 'src/main.js'),
      name: 'Girder',
      fileName: 'girder',
    },
    // rollupOptions: {
    //   external: ['vue'],
    //   output: {
    //     globals: {
    //       vue: 'Vue',
    //     },
    //   },
    // },
  },
})

