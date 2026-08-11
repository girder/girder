import fs from 'fs';
import path, { resolve } from 'path';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { compileClient } from 'pug';
import dts from 'vite-plugin-dts';
import { viteStaticCopy } from 'vite-plugin-static-copy';

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

function inlineFaviconPlugin(relFaviconPath, mimeType) {
  return {
    name: 'inline-favicon',
    transformIndexHtml(html, ctx) {
      if (ctx && ctx.server) {
        return html;
      }

      const faviconAbsPath = path.resolve(process.cwd(), relFaviconPath);
      try {
        const faviconData = fs.readFileSync(faviconAbsPath);
        const base64 = faviconData.toString('base64');
        const dataUri = `data:${mimeType};base64,${base64}`;
        return html.replace(
          /<link\s+rel="(?:shortcut\s+icon|icon)"[^>]*href=["'][^"']*["'][^>]*>/i,
          `<link rel="icon" type="${mimeType}" href="${dataUri}">`
        );
      } catch (err) {
        console.warn(`[inline-favicon] Failed to inline favicon ${relFaviconPath}:`, err);
        return html;
      }
    }
  };
}

let buildOpts = {};
const plugins: any[] = [];
let outDir = 'dist';

if (process.env.BUILD_LIB) {
  buildOpts = {
    lib: {
      entry: resolve(import.meta.dirname, 'src/index.ts'),
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
  base: './',
  plugins: [
    vue(),
    pugPlugin(),
    inlineFaviconPlugin('public/Girder_Favicon.png', 'image/png'),
    viteStaticCopy({
      targets: [
        {
          src: path.resolve(import.meta.dirname, './src') + '/[!.]*',
          dest: './src',
        },
      ],
    }).filter((config) => config.apply === 'build'), // Don't copy sources for dev server
    ...plugins,
  ],
  resolve: {
    alias: {
      '@girder/core': resolve(import.meta.dirname, 'src'),
    }
  },
  build: {
    sourcemap: !process.env.SKIP_SOURCE_MAPS,
    outDir,
    chunkSizeWarningLimit: Infinity,
    ...buildOpts,
    rollupOptions: {transform: {
    inject: {
      $: 'jquery',
      jQuery: 'jquery',
      exclude: 'src/**/*.pug',
    },
    },
    },
  },
});
