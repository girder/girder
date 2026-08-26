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
        // ignore missing favicon during test runs or builds
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

// Pass `PLAYWRIGHT_TESTING=true` when starting the dev server via playwright
// so it knows to disable hot reloading. Vite's file watching consumes inotify
// resources; since automated browsers don't need HMR, we completely disable it
// during Playwright test runs.
const isTestMode = process.env.PLAYWRIGHT_TESTING === 'true';

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
    }).filter((config) => config.apply === 'build'),  // Don't copy sources for dev server
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
    }},
  },
  server: {
    // Disable Hot Module Reloading when running under Playwright tests
    hmr: isTestMode ? false : {},
    watch: isTestMode ? null : {
      ignored: [
        '**/node_modules/**',
        '**/coverage/**',
        'dist/**',
        '**/*.pyc',
        '**/__pycache__/**',
        '**/.git/**',
      ],
    },
  },
});
