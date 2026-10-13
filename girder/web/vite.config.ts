import fs from 'fs';
import path, { resolve } from 'path';

import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { compileClient } from 'pug';
import istanbul from 'vite-plugin-istanbul';
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
const instrumentPlugins: any[] = [];
let outDir = 'dist';

// When requested, instrument the application source with istanbul so that the
// browser exposes accurate statement/branch/function coverage on
// window.__coverage__.  V8 coverage (used elsewhere) cannot represent
// statements inside functions that are never called, because it only reports
// executed ranges; instrumented coverage does not have that limitation.
if (process.env.GIRDER_TEST_COVERAGE && !process.env.BUILD_LIB) {
  instrumentPlugins.push(istanbul({
    include: 'src/**/*',
    exclude: ['node_modules/**', 'dist/**'],
    extension: ['.js', '.ts', '.vue', '.pug'],
    requireEnv: false,
    forceBuildInstrument: true,
  }));
}

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

export default defineConfig({
  base: './',
  plugins: [
    vue(),
    pugPlugin(),
    ...instrumentPlugins,
    inlineFaviconPlugin('public/Girder_Favicon.png', 'image/png'),
    viteStaticCopy({
      targets: [
        {
          src: path.resolve(import.meta.dirname, './src') + '/[!.]*',
          dest: './src',
        },
        {
          src: path.resolve(import.meta.dirname, './node_modules/swagger-ui-dist') + '/{swagger-ui.css,swagger-ui-bundle.js}',
          dest: './swagger-ui',
          rename: { stripBase: true },
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
    watch: {
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
